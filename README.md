## Sisqo – Cisco SSH automation library

### Overview

Sisqo is a library for automating the management of Cisco devices via SSH.

#### Features

 * Runs on any UNIX-style platform that has vty support, with no dependencies on OpenSSH or SSH agents
 * Emulates OpenSSH-style `ProxyCommand` support, allowing the library to traverse jumpboxes
 * Supports SSH pubkey authentication with no dependency on the user's `.ssh` profile, complimenting the `ProxyCommand` feature by attempting both password-based and pubkey-based authentication at each hop
 * Complete support for VT100 series terminal emulation, guaranteeing that what you see on the command line will also be what you receive from this library
 * Automatically handles Cisco-style "more" pagination and prompt matching, allowing for seamless `read()`/`write()` semantics regardless of the target device's terminal settings
 * Provides special API support for `enable` authorization
 * Provides a fluid API for parsing `running-config` and `startup-config` into strongly typed hierarchical objects that can be traversed with regex-based searching
 * Tested against Cisco IOS, Catalyst, Nexus, ASA/PIX, and ASR series devices

#### Usage

To use the Sisqo library, you must have a recent version of the `pip` Python package manager. First, `git clone` this repository into a local directory. Open a shell at the repository path, and `pip install -r requirements.txt` to install Sisqo's runtime dependencies.

At this point, you may copy the Sisqo repository folder into your Python project and `import Sisqo` to begin using the library.


## API Documentation

**Example code:**

```python
from sys import exit

import sisqo

router = sisqo.SSH( host='router.example.com',
                    proxyCommand='ssh -W %h:%p jdoe@jumpbox.example.com' )

with router:

    if not router.authenticate(
        username='cisco',
        password='cisco',
        privateKeyFile='~/.ssh/id_rsa',
        privateKeyPassword='password123' ):
        
        exit( 1 )  # could not authenticate with the router

    if not router.enable( password='cisco' ):
    
        exit( 2 )  # could not enable on the router

    router.write( 'show version' )
    versionInformation = router.read()

    print( 'Router version:' )
    print( versionInformation )  # Cisco IOS Software, C2900 Software (C2900-UNIVERSALK9-M) ...

    runningConfig = router.showRunningConfig()

    bgpConfig = runningConfig.findChild( 'router bgp \d+' )

    bgpNeighbors = bgpConfig.findChildren( 'neighbor .+' )

    print( 'BGP neighbors of ASN %s:' %(bgpConfig.value.split()[2]) )  # BGP neighbors of ASN 12345:
    
    for neighbor in bgpNeighbors:
    
        ipAddress = neighbor.value.split()[1]
        print( ipAddress )  # 11.22.33.44

    router.write( 'write memory' )
    wrMemResult = router.read()
    
    if '[ok]' not in wrMemResult.lower():
    
        exit( 3 )  # could not save the running-config to the router

exit( 0 )
```

### class _SSH_

*_Note_: this class must be used as a context manager (using a "with" statement)*

 * **constructor ( _host_: str, _port_: int?, _proxyCommand_: str? )**

   Creates an object that can be used to SSH into the provided `host`/`port` and issue commands. To proxy through a jumpbox, provide an OpenSSH-style `proxyCommand`.

 * **readonly property _host_: str** – hostname or IP address to SSH into

 * **readonly property _port_: int** – port number to SSH into

 * **readonly property _proxyCommand_: str | None** – SSH command used to connect to the jumpbox

 * **method _authenticate_ ( _username_: str, _password_: str?, _privateKeyFile_: str?, _privateKeyPassword_: str? ): bool**

   Initiates an SSH connection to the target device, trying the specified private key and proxying through intermediate jumpboxes if necessary.

 * **method _read_ ( _timeout_: int?, _promptRegex_: str?, _moreRegex_: str?, _stripPrompt_: bool? ): str**

   Reads from the target device up to the next prompt, with special handling for Cisco-style pagination. If a prompt cannot be matched in the output, the read operation returns after `timeout` seconds. The `stripPrompt` argument can be used to control whether or not the text of the prompt is returned as part of the read operation.

 * **method _write_ ( _command_: str , _consumeEcho_: bool? )**

   Writes `command` to the target device. By default, this function expects the device to echo back `command`. If `consumeEcho` is True (the default), this function will implicitly consume the data that is echoed back. When responding to password prompts, you should set `consumeEcho` to False to avoid unintentionally consuming data.

   *_Warning_: this function implicitly reads any previously unread data without returning it to the consumer.*

 * **method _enable_ ( _password_: str ): bool**

   Helper function to elevate privileges on a target device, with special handling for the "Password" prompt.

   *_Warning_: enable is not supported on certain Cisco operating systems*

 * **method _showRunningConfig_ ( ): Configuration**

   Helper function to retrieve the target device's *running-config* and parse it into a `Configuration` object.

 * **method _showStartupConfig_ ( ): Configuration**

   Helper function to retrieve the target device's *startup-config* and parse it into a `Configuration` object.

   *_Warning_: startup-config is not supported on certain Cisco operating systems*



### class _Configuration_

*_Note_: instances of this class are returned from `SSH.showRunningConfig()` and `SSH.showStartupConfig()`*


 * **constructor ( _configString_: str )**

   Parses a Cisco configuration file `configString` into a hierarchical, searchable representation of configuration lines.

 * **method _findChild_ ( _regex_: str ): Line**

   Searches the root node of the hierarchy for the first line that matches the provided `regex`.

 * **method _findChildren_ ( _regex_: str ): list[Line]**

   Searches the root node of the hierarchy for lines that match the provided `regex`.


### class _Line_

*_Note_: instances of this class are returned from `Configuration.findChild()` and `Configuration.findChildren()`*

 * **constructor ( _number_: int, _indent_: str, _value_: str )**

   Creates a strong representation of a single line of a Cisco configuration file

 * **property _parent_: Line** – hierarchical parent of this configuration line

 * **property _children_: list[Line]** – list of hierarchical children of this configuration line

 * **readonly property _value_: str** – text of the configuration line, stripped of indentation

 * **readonly property _lineNumber_: int** – line number from the original configuration text

 * **readonly property _indentation_: int** – indentation level of the configuration line

 * **readonly property _depth_: int** – depth of this line in the configuration hierarchy

 * **method _findChild_ ( _regex_: str ): Line**

   Searches the children of this node for the first line that matches the provided `regex` and returns that line.

 * **method _findChildren_ ( _regex_: str ): list[Line]**

   Searches the children of this node for lines that match the provided `regex` and returns a list of matching lines.
