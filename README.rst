Sisqo
=====

**A better library for automating network gear with Cisco-style command line interfaces.**

:Author:
    Alex Forster (alex@alexforster.com)
:License:
    BSD 3-Clause

**Features**

-  Provides a fluid API for parsing ``running-config`` and
   ``startup-config`` into strongly typed hierarchical objects that can
   be traversed with regex-based searching
-  Complete support for VT100-series terminal emulation, guaranteeing
   that what you see on the command line will also be what you receive
   from this library
-  Automatically handles Cisco-style "more" pagination and prompt
   matching, allowing for seamless ``read()``/``write()`` semantics
   regardless of the target device's terminal settings
-  Provides special API support for ``enable`` authorization
-  Runs on any platform that has the OpenSSH binary installed
-  Tested against Cisco IOS, Catalyst, Nexus, ASA/PIX, and ASR series
   devices

**Installation**

``pip install sisqo``

| **GitHub:** https://github.com/alexforster/sisqo/tree/v2.1.1
| **PyPI:** https://pypi.python.org/pypi/sisqo/2.1.1

**Dependencies:**

- ``ptyprocess`` – a library for launching a subprocess in a pseudo terminal (pty)
- ``pyte`` – an in memory VTXXX-compatible terminal emulator library

  - ``wcwidth`` – a library for wide-character width calculation

Example Code
------------

.. code-block:: python

    from sys import exit

    import sisqo

    router = sisqo.SSH('router.example.com', username='jdoe')

    switch.onRead(lambda data: sys.stderr.write(str(data)))
    switch.onWrite(lambda data: sys.stderr.write(str(data)))

    with router:

        if not router.authenticate('password123'):

            exit(1)  # could not authenticate with the router

        if not router.enable('123456'):

            exit(2)  # could not enable on the router

        router.write('show version')
        versionInformation = router.read()  #= "Cisco IOS Software, C2900 Software (C2900-UNIVERSALK9-M) ..."
        print(versionInformation)

        runningConfig = router.showRunningConfig()

        # hostname router1
        # !
        # interface GigabitEthernet0/0
        #   shutdown
        # interface GigabitEthernet0/1
        #   shutdown
        # !
        # router bgp 12345
        #   network 55.66.77.88/24
        #   neighbor 11.22.33.44
        #     remote-as 54321
        #     timers 7 21
        #   neighbor 22.33.44.55
        #     remote-as 98765
        #     timers 7 21

        routerBGP = runningConfig.findChild('router bgp \d+')  #= "router bgp 12345"
        asn = routerBGP.value.split()[-1]  #= "12345"

        print('BGP neighbors of ASN {}'.format(asn))

        bgpNeighbors = routerBGP.findChildren('neighbor .+')

        for neighbor in bgpNeighbors:  #= [<neighbor 11.22.33.44>, <neighbor 22.33.44.55>]

            ipAddress = neighbor.value  #= "neighbor 11.22.33.44"
            ipAddress = ipAddress.split()[-1]  #= "11.22.33.44"

            print("Neighbor: {}".format(ipAddress))
