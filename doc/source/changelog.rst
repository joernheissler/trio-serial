.. _changelog:

Changelog
=========
.. _changelog.0.3.0:

0.3.0 - 2021-05-15
------------------
* Fix cleanup issue when running in sync context. Remove ``close`` method.
  (`#4 <https://github.com/joernheissler/trio-serial/issues/4>`__)

.. _changelog.0.2.1:

0.2.1 - 2021-04-09
------------------
* Do not handle modem bits (e.g. rts) in constructor / aopen. Use
  :py:meth:`~trio_serial.abstract.AbstractSerialStream.set_rts`/\
  :py:meth:`~trio_serial.abstract.AbstractSerialStream.get_rts`
  instead. (`#2 <https://github.com/joernheissler/trio-serial/issues/2>`__)
* Add new methods to control "hangup on close":

  - :py:meth:`~trio_serial.abstract.AbstractSerialStream.get_hangup`
  - :py:meth:`~trio_serial.abstract.AbstractSerialStream.set_hangup`

.. _changelog.0.1.2:

0.1.2 - 2021-02-07
------------------
* More relaxed dependencies

.. _changelog.0.1.1:

0.1.1 - 2021-01-31
------------------
* Add new methods:

  - :py:meth:`~trio_serial.abstract.AbstractSerialStream.port`
  - :py:meth:`~trio_serial.abstract.AbstractSerialStream.discard_input`
  - :py:meth:`~trio_serial.abstract.AbstractSerialStream.discard_output`
  - :py:meth:`~trio_serial.abstract.AbstractSerialStream.send_break`

.. _changelog.0.1.0:

0.1.0 - 2020-12-21
------------------
* Initial release.
