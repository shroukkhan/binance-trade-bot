from contextvars import ContextVar
from typing import List, Optional


def _default_list() -> Optional[List]:
    return None


should_postpone = ContextVar("should_postpone", default=False)
postponed_calls = ContextVar("postponed_calls", default=_default_list())


def heavy_call(func):
    """
    Defines a function that is considered slow and can be scheduled to execute later

    The heavy_call functions are executed in the order they were called. If there was no previous call to
    postpone_heavy_calls function before the execution is immediate, otherwise function and call args are saved for
    later execution when postpone_heavy_calls function done its work.

    Note: dont expect a result from heavy_call function being return, they may be viewed as procedures,
    whose exact execution moment isn't relevant like commit/write to db or heavy logging.
    """

    def wrap(*args, **kwargs):
        if should_postpone.get():
            postponed_calls.get().append((func, args, kwargs))
        else:
            func(*args, **kwargs)

    return wrap


def postpone_heavy_calls(func):
    """
    Defines the function that is performance critical and postpones execution of slower functions

    See heavy_call

    Note: when several calls to postpone_heavy_calls functions are nested - the outtermost one takes priority like
    inner ones are just regular functions.
    """

    def wrap(*args, **kwargs):
        if should_postpone.get():
            func(*args, **kwargs)
        else:
            should_postpone.set(True)
            if postponed_calls.get() is None:
                postponed_calls.set([])
            try:
                func(*args, **kwargs)
            finally:
                should_postpone.set(False)
                pcs = postponed_calls.get()
                for pfunc, pargs, pkwargs in pcs:
                    pfunc(*pargs, **pkwargs)
                pcs.clear()

    return wrap
