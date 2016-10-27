Sisqo
=====

**Author:** Alex Forster (alex@alexforster.com) **License:** BSD
3-Clause

Overview
~~~~~~~~

Sisqo is a better library for automating network gear with Cisco-style
command line interfaces.

Features
~~~~~~~~

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

Installation
~~~~~~~~~~~~

``pip install sisqo``

**PyPI:** https://pypi.python.org/pypi/sisqo/2.0.0

**Dependencies:**

-  ``ptyprocess`` – a library for launching a subprocess in a pseudo
   terminal (pty)
-  ``pyte`` – an in memory VTXXX-compatible terminal emulator library
-  ``wcwidth`` – a library for wide-character width calculation

API Documentation
-----------------

**Example code:**

.. code:: python

    from sys import exit

    import sisqo

    router = sisqo.SSH(host='router.example.com', username='jdoe')

    with router:

        if not router.connect('password123'):
            
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

        routerBGP = runningConfig.findChild('router bgp \d+').value  #= "router bgp 12345"
        asn = int(routerBGP.split()[-1])  #= 12345
        
        print('BGP neighbors of ASN {}'.format(asn))
        
        bgpNeighbors = bgpConfig.findChild('router bgp \d+').findChildren('neighbor .+') 

        for neighbor in bgpNeighbors:  #= [<neighbor 11.22.33.44>, <neighbor 22.33.44.55>]
        
            ipAddress = neighbor.value  #= "neighbor 11.22.33.44"
            ipAddress = ipAddress.split()[-1]  #= "11.22.33.44"
            
            print("Neighbor: {}".format(ipAddress))

class *SSH*
~~~~~~~~~~~

*Note: this class can be used as a context manager (using a "with"
statement)*

-  **\_\_init\_\_ ( *username*: str, *host*: str, *port*: int?,
   *sshConfigFile*: str? )**

Creates an object that initiates an SSH connection as ``username`` to
the provided ``host`` and ``port`` (default: *22*).

The OpenSSH client, by default, will obey the system's
``/etc/ssh/ssh_config`` file as well as the current user's
``~/.ssh/config`` file. You can provide a path to `a custom ssh\_config
file <http://man.openbsd.org/ssh_config>`__ using the ``sshConfigFile``
argument, which will prevent these default configuration files from
being considered.

-  ***host*: readonly str**

Hostname or IP address to SSH into

-  ***port*: readonly int**

Port number to connect to

-  ***promptRegex*: str**

Regular Expression used to match shell prompts

-  ***moreRegex*: str**

Regular Expression used to match Cisco-style "more" pagination prompts

-  ***authenticate* ( *password*: str?, *passphrase*: str?,
   *promptCallback*: lambda?, *promptState*: dict? )**

Allows the user to reliably respond to an authentication prompt
(``password`` and/or private key ``passphrase``) if necessary.

This method also provides a convenient way to handle alternative
prompts, for situations where something other than a password or
passphrase are required (for example, a TOTP multi-factor challenge
code).

The ``promptCallback`` parameter should be a function that responds to
the alternative prompt. It will be called repeatedly until it either
returns a correct response, or it returns *None* to indicate that it
cannot answer the prompt successfully. The signature of the callback is:
``(prompt: str, state: dict[str, object], logger: logging.Logger) => bool|None``

The ``promptState`` parameter is a way to pass in persistent state
information to the prompt callback via a dictionary. The same dictionary
will be passed in for successive calls to ``promptCallback``. It is
seeded with *password* and *passphrase* properties by the
``authenticate`` method, corresponding to the provided arguments of the
same name.

For example, to try guessing multiple passwords, one could do the
following–

\`\`\`python from sys import exit import ssh

state = { 'passwordsToTry': ['cisco', '123456', 'password123'] }

def onPrompt(prompt, state, logger):

::

      if 'password:' not in prompt.lower(): return None
      
      if len(state['passwordsToTry']) == 0: return None
      
      return state['passwordsToTry'].pop()

with sisqo.SSH(host='router.example.com', username='cisco') as router:

::

      if not router.authenticate(promptCallback=onPrompt, promptState=state):
      
          exit(1)  # none of the passwords we tried worked
      
      # successfully authenticated using one of the three passwords we tried
      router.write('show version')

\`\`\`

-  ***read* ( *timeout*: int?, *stripPrompt*: bool?, *promptRegex*: re?
   ): str**

Reads from the target device up to the next prompt, with special
handling for Cisco-style "more" pagination. If a prompt cannot be
matched in the output, the read operation returns after ``timeout``
seconds (default: *10*). The ``stripPrompt`` argument can be used to
control whether or not the text of the prompt is returned as part of the
read operation (default: *True*). The ``promptRegex`` argument (default:
*None*), if specified, overrides the class's ``promptRegex`` property.

-  ***write* ( *command*: str, *timeout*: int?, *consumeEcho*: bool? )**

Writes ``command`` to the target device. This function can optionally
suppress the terminal's echoback. If ``consumeEcho`` is True (the
default), this function will implicitly read up to ``len(command)``
bytes or until ``timeout`` seconds has passed (default: *10*). When
manually responding to password prompts, you should set ``consumeEcho``
to *False* if the password is not typically echoed back to you as
asterisks or otherwise.

*Warning: this function implicitly discards any previously unread data
without returning it to the consumer.*

-  ***enable* ( *password*: str ): bool**

Helper function to elevate privileges on the target network gear, with
special handling for the "Password" prompt.

*Warning: enable is not supported on certain Cisco-alike operating
systems*

-  ***showRunningConfig* ( ): Configuration**

Helper function to retrieve the target device's *running-config* and
parse it into a ``Configuration`` object.

-  ***showStartupConfig* ( ): Configuration**

Helper function to retrieve the target device's *startup-config* and
parse it into a ``Configuration`` object.

*Warning: startup-config is not supported on certain Cisco-alike
operating systems*

-  ***disconnect* ( )**

Closes the SSH connection with the target device, if open. Called
automatically when exiting a context manager and/or when the object is
garbage collected.

class *Configuration*
~~~~~~~~~~~~~~~~~~~~~

*Note: instances of this class are returned from
``SSH.showRunningConfig()`` and ``SSH.showStartupConfig()``*

-  **\_\_init\_\_ ( *configString*: str )**

Parses a Cisco configuration file ``configString`` into a hierarchical,
searchable representation of configuration lines.

-  ***findChild* ( *regex*: str ): Line**

Searches the root node of the hierarchy for the first line that matches
the provided ``regex``.

-  ***findChildren* ( *regex*: str ): list[Line]**

Searches the root node of the hierarchy for lines that match the
provided ``regex``.

class *Line*
~~~~~~~~~~~~

*Note: instances of this class are returned from
``Configuration.findChild()`` and ``Configuration.findChildren()``*

-  **\_\_init\_\_ ( *number*: int, *indent*: str, *value*: str )**

Creates an in-memory representation of a single line of a Cisco
configuration file.

-  ***findChild* ( *regex*: str ): Line**

Searches the children of this node for the first line that matches the
provided ``regex`` and returns that line.

-  ***findChildren* ( *regex*: str ): list[Line]**

Searches the children of this node for lines that match the provided
``regex`` and returns a list of matching lines.

-  **property *value*: str**

Text of this configuration line, stripped of indentation

-  ***parent*: Line**

Hierarchical parent of this configuration line

-  ***children*: list[Line]**

List of hierarchical children of this configuration line

-  ***lineNumber*: int**

Line number from the original configuration text

-  ***indentation*: readonly int**

Indentation level of this configuration line

-  ***depth*: readonly int**

Depth of this line in the configuration hierarchy

class *NotConnectedError* : *Exception*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thrown when certain operations are tried on an ``SSH`` instance which is
not connected.

class *NotAuthenticatedError* : *Exception*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thrown when certain operations are tried on an ``SSH`` instance which
has not yet authenticated.

class *AlreadyAuthenticatedError* : *Exception*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thrown when authentication is tried on an ``SSH`` instance which has
already authenticated.

class *BadAuthenticationError* : *Exception*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thrown when authentication fails.
