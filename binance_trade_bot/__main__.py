from contextvars import copy_context

from .crypto_trading import main

if __name__ == "__main__":
    ctx = copy_context()
    try:
        ctx.run(main())
    except KeyboardInterrupt:
        pass
