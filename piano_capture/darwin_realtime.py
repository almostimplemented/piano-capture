import ctypes, ctypes.util
import sys
import time
import logging
import numpy as np

cocoa = ctypes.cdll.LoadLibrary(ctypes.util.find_library("Cocoa"))

# see thread_policy.h (Darwin)
THREAD_STANDARD_POLICY = ctypes.c_int(1)
THREAD_STANDARD_POLICY_COUNT = ctypes.c_int(0)
THREAD_TIME_CONSTRAINT_POLICY = ctypes.c_int(2)
THREAD_TIME_CONSTRAINT_POLICY_COUNT = ctypes.c_int(4)
KERN_SUCCESS = 0


class TimeConstraintPolicyParameters(ctypes.Structure):
    _fields_ = [
        ("period", ctypes.c_uint),
        ("computation", ctypes.c_uint),
        ("constrain", ctypes.c_uint),
        ("preemptible", ctypes.c_int),
    ]


def enable_realtime():
    policy = thread_policy(use_default=True, flavour=THREAD_TIME_CONSTRAINT_POLICY)
    err = cocoa.thread_policy_set(
        cocoa.mach_thread_self(),
        THREAD_TIME_CONSTRAINT_POLICY,
        ctypes.byref(policy),  # send the address of the struct
        THREAD_TIME_CONSTRAINT_POLICY_COUNT,
    )
    if err != KERN_SUCCESS:
        raise RuntimeError("Failed to set thread policy with thread_policy_set")
    else:
        params = (
            np.array(
                [
                    policy.period,
                    policy.computation,
                    policy.constrain,
                ]
            )
            / 1000.0
        )
        logging.info(
            "Successfully set thread to realtime (parameters: %d %d %d)".format(
                x[1] for x in enumerate(params)
            )
        )


def thread_policy(use_default, flavour):
    """Retrieve the current (or default) thread policy.

    use_default should be True or False
    flavour should be 1 (standard) or 2 (realtime)

    Returns a ctypes struct with fields:
    .period
    .computation
    .constrain
    .preemptible

    See http://docs.huihoo.com/darwin/kernel-programming-guide/scheduler/chapter_8_section_4.html
    """

    policy = TimeConstraintPolicyParameters()
    use_default = ctypes.c_int(
        use_default
    )  # we want to retrieve actual policy or the default
    err = cocoa.thread_policy_get(
        cocoa.mach_thread_self(),
        THREAD_TIME_CONSTRAINT_POLICY,
        ctypes.byref(policy),  # send the address of the policy struct
        ctypes.byref(THREAD_TIME_CONSTRAINT_POLICY_COUNT),
        ctypes.byref(use_default),
    )
    return policy
