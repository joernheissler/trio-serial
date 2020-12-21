.. _example:

Example
=======
.. code-block:: python

    from trio import run
    from trio_serial import SerialStream

    async def main():
        async with SerialStream("/dev/ttyUSB0") as ser:
            for i in range(10):
                buf = await ser.receive_some()
                await ser.send_all(buf)
                await ser.send_all(buf)

    run(main)
