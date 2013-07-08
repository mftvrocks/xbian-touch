#!/usr/bin/env python
import ctypes, fcntl, os, sys
import select

import uinputmapper
import uinputmapper.linux_uinput
from uinputmapper.cinput import *
from uinputmapper.mapper import KeyMapper, parse_conf, pretty_conf_print

try:
    import cPickle as pickle
except ImportError:
    import pickle

import optparse

_usage = 'input-read /dev/input/event<0> ... /dev/input/event<N>'
parser = optparse.OptionParser(description='Read input devices.',
        usage = _usage,
        version='0.01')
parser.add_option('-D', '--dump', action='store_false',
        default=True, help='Dump will marshall all the events to stdout')
parser.add_option('-v', '--verbose', action='store_true',
        default=False, help='Enable verbose mode (do not combine with -D)')

parser.add_option('-C', '--compat', action='store_true',
        help='Enable compatibility mode; for Python < 2.7')

args, input_file = parser.parse_args()

if len(input_file) == 0:
    parser.print_help()
    exit(0)

# Open input devices
fs = map(InputDevice, input_file)

# Create configuration
config = {}
for idx, f in enumerate(fs):
    c = parse_conf(f, idx)

    config.update(c)

if args.verbose:
    pretty_conf_print(config)

poll_obj, poll_mask = (select.poll, select.POLLIN) if args.compat else \
        (select.epoll, select.EPOLLIN)

# Add all devices to epoll
pp = poll_obj()
for f in fs:
    pp.register(f.get_fd(), poll_mask)

f.grab()

# Human readable info
if args.dump:
    for f in fs:
        print 'Version:', f.get_version()
        print f.get_name()

        d = f.get_exposed_events()
        for k, v in d.iteritems():
            print k + ':', ', '.join(v)

else:
    # Dump initial information over pickle to stdout
    p = pickle.Pickler(sys.stdout)

    p.dump(len(fs))

    p.dump(config)

    sys.stdout.flush()

while True:
    events = pp.poll()

    for e in events:
        fd, ev_mask = e

        if not ev_mask & poll_mask:
            continue

        # Lets undo that epoll speedup ;-) FIXME XXX
        for idx, _ in enumerate(fs):
            if _.get_fd() == fd:
                f = _
                i = idx

        ev = f.next_event()

        if args.dump:
            try:
                print i, ev.time.tv_sec, ev.time.tv_usec
                s = '%s %s %d' % (rev_events[ev.type],
                        rev_event_keys[ev.type][ev.code], ev.value)
                print 'Event type:', s
            except KeyError:
               pass

        else:
            if not args.compat:
                p.dump((i, ev))
            else:
                p.dump((i, (ev.time.tv_sec, ev.time.tv_usec,
                    ev.type, ev.code, ev.value)))

            sys.stdout.flush()
