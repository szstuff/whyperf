# whyperf
network performance utility inspired by iPerf developed for an exam in the DATA2410 course

Requires Python3
**Usage**

python3 whyperf.py [-s] [-c] [-b BIND] [-p PORT] [-f FORMAT] [-I SERVERIP] [-t TIME] [-n NUM] [-i INTERVAL] [-P PARALLEL]

**Arguments**


  -h, --help - show this help message and exit

  -s, --server - Start in server mode. Default

  -c, --client - Start in client mode

  -b BIND, --bind BIND - Bind to provided IPv4 address. Default 127.0.0.1

  -p PORT, --port PORT - Bind to provided port. Default 8088

  -f FORMAT, --format FORMAT - Specify output format. Supported: B, KB, MB. Default MB

  -I SERVERIP, --serverip SERVERIP

  -t TIME, --time TIME - Duration of test in seconds

  -n NUM, --num NUM - Number of bytes to transfer. Must end with B, KB or MB

  -i INTERVAL, --interval INTERVAL - Update frequency for statistics in seconds

  -P PARALLEL, --parallel PARALLEL - Create parallel connections to server

