# -*- encoding: utf-8 -*-


def _send_event(action, data):
    tag = 'ceph-salt/{action}'.format(action=action)
    __salt__['event.send'](tag, data=data)


def _send_begin_event(action, data):
    _send_event("{action}/begin".format(action=action), data)


def _send_end_event(action, data):
    _send_event("{action}/end".format(action=action), data)


def state(name, step, state_name, state_args=None, state_kwargs=None):
    state_args = [] if state_args is None else state_args
    state_kwargs = {} if state_kwargs is None else state_kwargs
    _send_begin_event(step, {'id': name, 'mod': state_name})
    if 'name' not in state_kwargs and not state_args:
        state_kwargs['name'] = name
    res = __states__[state_name](*state_args, **state_kwargs)
    _send_end_event(step, {'id': name, 'mod': state_name, 'ret': res})
    return res
