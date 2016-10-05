"""Combine all the modules."""

from __future__ import print_function

from collections import namedtuple

import logging

from thrifty.block_data import card_reader
from thrifty.detect import Detector
from thrifty import identify
from thrifty import matchmaker
from thrifty import tdoa_est


DEFAULT_DETECTOR = Detector  # pylint: disable=invalid-name
DEFAULT_INTEGRATOR = identify.integrate
DEFAULT_MATCHER = matchmaker.match_toads
DEFAULT_TDOA_EST = tdoa_est.process
# DEFAULT_POS_EST =


PostdetectSettings = namedtuple('PostdetectSettings', [
    'tx_freqs', 'match_window', 'tdoa_est_window',
    'rx_pos', 'beacon_pos', 'sample_rate'])

PostdetectResult = namedtuple('PostdetectResult', [
    'toads', 'matches', 'tdoas', 'pos'])


def patch_module(module, **override):
    """Override a module's parameters."""
    def _patched_module(*args, **kwargs):
        kwargs.update(override)
        module(*args, **kwargs)
    return _patched_module


def detect_all(cards, settings, detector=DEFAULT_DETECTOR):
    """Detect positioning signal and estimate SOA."""
    toad = []
    for rxid, card in cards.iteritems():
        logging.info(" * Detect: RX #%d (%s)", rxid, card)
        blocks = card_reader(open(card, 'r'))
        det = detector(settings, blocks, rxid=rxid)
        toad.extend([result for detected, result in det if detected])
    return toad


def postdetect(toad, settings,
               integrator=DEFAULT_INTEGRATOR,
               matcher=DEFAULT_MATCHER,
               tdoa_estimator=DEFAULT_TDOA_EST):
    """Identify, match, estimate TDOA, estimate position."""

    # Identify transmitters and remove duplicates
    logging.info(" * Integrate")
    toads = integrator(toad, nominal_freqs=settings.tx_freqs)

    # Match detections
    logging.info(" * Match")
    matches, _ = matcher(toads, settings.match_window)

    # Estimate TDOAs
    logging.info(" * TDOA estimate")
    tdoas, _, _ = tdoa_estimator(toads=toads,
                                 matches=matches,
                                 window_size=settings.tdoa_est_window,
                                 beacon_pos=settings.beacon_pos,
                                 rx_pos=settings.rx_pos,
                                 sample_rate=settings.sample_rate)

    # Estimate positions
    logging.info(" * Positions estimate")
    pos = None

    return PostdetectResult(toads=toads,
                            matches=matches,
                            tdoas=tdoas,
                            pos=pos)
