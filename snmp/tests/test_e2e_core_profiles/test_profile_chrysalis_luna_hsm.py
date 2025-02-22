# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_tcp,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_chrysalis_luna_hsm(dd_agent_check):
    config = create_e2e_core_test_config('chrysalis-luna-hsm')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:chrysalis-luna-hsm',
        'snmp_host:chrysalis-luna-hsm.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_tcp(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.hsmCriticalEvents', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hsmNonCriticalEvents', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hsmOperationErrors', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hsmOperationRequests', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ntlsConnectedClients', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ntlsFailedClientConnections', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ntlsLinks', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ntlsSuccessfulClientConnections', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'chrysalis-luna-hsm Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'chrysalis-luna-hsm.device.name',
        'profile': 'chrysalis-luna-hsm',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.12383.3.1.1',
        'vendor': 'chrysalis',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
