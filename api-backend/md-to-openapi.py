#!/usr/bin/env python3
# Copyright 2026 Open HamClock Standards
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may find a copy of the License in the LICENSE file at the repo root.

"""
Generate hamclock-openapi.yaml from api-doc.md
"""

import sys
import yaml

def generate_openapi(md_file, output_file):
    entries = []

    with open(md_file, 'r') as f:
        lines = f.readlines()

    table_start = False
    header_skipped = False
    for line in lines:
        line = line.strip()
        if line == '---':
            table_start = True
            continue
        if table_start and line.startswith('|'):
            if not header_skipped:
                header_skipped = True
                continue
            if line.find(':---') != -1:
                continue
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) == 9:
                path, arg, units, min_, max_, default, required, samples, prop = parts
                entries.append({
                    'path': path,
                    'arg': arg,
                    'units': units,
                    'min': min_,
                    'max': max_,
                    'default': default,
                    'required': required,
                    'samples': samples,
                    'proposal': prop
                })

    # Group by path
    paths = {}
    current_path = None
    params = []
    path_proposals = {}

    for entry in entries:
        if entry['path']:
            if current_path:
                paths[current_path] = {'parameters': params, 'proposal': path_proposals.get(current_path, '')}
                params = []
            current_path = entry['path']
            if entry['proposal']:
                path_proposals[current_path] = entry['proposal']

        if entry['arg']:
            # Infer type
            sample_vals = entry['samples'].split(', ') if entry['samples'] else []
            if sample_vals and all(v.replace('.', '').replace('-', '').isdigit() for v in sample_vals[:3]):
                param_type = 'number'
            else:
                param_type = 'string'

            param = {
                'name': entry['arg'],
                'in': 'query',
                'schema': {'type': param_type},
                'required': bool(entry['required'].strip())  # if not empty, true
            }
            if entry['default']:
                param['schema']['default'] = entry['default']
            params.append(param)

    if current_path:
        paths[current_path] = {'parameters': params, 'proposal': path_proposals.get(current_path, '')}

    # Build OpenAPI structure
    openapi_spec = {
        'openapi': '3.1.0',
        'info': {
            'title': 'HamClock API',
            'description': 'API endpoints for HamClock — a real-time amateur radio clock and propagation display application.',
            'version': '1.0.0',
            'license': {
                'name': 'CC BY-ND 4.0',
                'url': 'https://creativecommons.org/licenses/by-nd/4.0/'
            },
            'contact': {
                'name': 'HamClock',
                'url': 'https://www.clearskyinstitute.com/ham/HamClock/'
            }
        },
        'servers': [
            {'url': 'http://clearskyinstitute.com', 'description': 'Clear Sky Institute (primary)'},
            {'url': 'http://ohb.hamclock.app', 'description': 'OHB HamClock instance'},
            {'url': 'http://hamclock.com', 'description': 'HamClock.com'}
        ],
        'tags': [
            {'name': 'Solar Weather', 'description': 'Solar flux, X-ray, Bz, solar wind, and space weather data'},
            {'name': 'Geomagnetic', 'description': 'Geomagnetic indices including K-index and DST'},
            {'name': 'Propagation', 'description': 'HF band condition and MUF prediction scripts'},
            {'name': 'Reporters', 'description': 'PSK Reporter, RBN, and WSPR spot data'},
            {'name': 'Maps', 'description': 'Day and night map overlays at various resolutions'},
            {'name': 'SDO Images', 'description': 'Solar Dynamics Observatory solar imagery'},
            {'name': 'Satellites', 'description': 'Satellite tracking data'},
            {'name': 'Weather', 'description': 'World weather and local weather data'},
            {'name': 'Miscellaneous', 'description': 'Contests, DXpeditions, city data, version info, and more'}
        ],
        'paths': {}
    }

    # Add paths
    for path, data in paths.items():
        # Determine tag based on path
        tag = 'Miscellaneous'
        if '/SDO/' in path: tag = 'SDO Images'
        elif '/maps/' in path: tag = 'Maps'
        elif any(x in path for x in ['/solar-', '/Bz/', '/NOAASpaceWX/', '/ssn/', '/xray/', '/solar-wind/']): tag = 'Solar Weather'
        elif '/geomag/' in path or '/dst/' in path: tag = 'Geomagnetic'
        elif any(x in path for x in ['fetchVOACAP', 'fetchBandConditions']): tag = 'Propagation'
        elif any(x in path for x in ['Reporter', 'RBN', 'WSPR']): tag = 'Reporters'
        elif '/wx' in path or '/worldwx/' in path: tag = 'Weather'
        elif '/esats/' in path: tag = 'Satellites'

        description = 'Standard HamClock API endpoint.'
        if data['proposal']:
            description = f"Proposal implementation: {data['proposal']}."

        openapi_spec['paths'][path] = {
            'get': {
                'tags': [tag],
                'summary': path.split('/')[-1],
                'description': description,
                'parameters': data['parameters'],
                'responses': {
                    '200': {
                        'description': 'Success',
                        'content': {
                            'text/plain': {'schema': {'type': 'string'}}
                        }
                    }
                }
            }
        }

    with open(output_file, 'w') as f:
        yaml.dump(openapi_spec, f, default_flow_style=False, sort_keys=False)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 md-to-openapi.py <api-doc.md> <hamclock-openapi.yaml>")
        sys.exit(1)

    md_file = sys.argv[1]
    output_file = sys.argv[2]
    generate_openapi(md_file, output_file)