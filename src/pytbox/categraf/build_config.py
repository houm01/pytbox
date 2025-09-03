#!/usr/bin/env python3

import os
from pathlib import Path
from pytbox.utils.load_config import load_config_by_file
from glob import glob
import os
from jinja2 import Environment, FileSystemLoader


jinja2_path = Path(__file__).parent / 'jinja2'
env = Environment(loader=FileSystemLoader(jinja2_path))

ping_template = env.get_template('input.ping/ping.toml.j2')
prometheus_template = env.get_template('input.prometheus/prometheus.toml.j2')


class BuildConfig:
    '''
    生成配置

    Args:
        instances (_type_): _description_
        output_dir (_type_): _description_
    '''
    def __init__(self, instances, output_dir):
        self.instances = load_config_by_file(instances)
        self.output_dir = output_dir
    
    def _get_template(self, template_name):
        return env.get_template(template_name)

    def common(self, input_name):
        template = self._get_template(f'input.{input_name}/{input_name}.toml.j2')
        render_data = template.render()
        target_dir = Path(self.output_dir) / f'input.{input_name}'
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            
        with open(Path(self.output_dir) / f'input.{input_name}' / f'{input_name}.toml', 'w', encoding='utf-8') as f:
            f.write(render_data)

    def ping(self):
        if self.instances.get('ping'):
            instances = self.instances['ping']['instance']
            render_data = ping_template.render(instances=instances)
            target_dir = Path(self.output_dir) / 'input.ping'
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                
            with open(Path(self.output_dir) / 'input.ping' / 'ping.toml', 'w', encoding='utf-8') as f:
                f.write(render_data)

    def prometheus(self):
        if self.instances.get('prometheus'):
            instances = self.instances['prometheus']['urls']
            render_data = prometheus_template.render(instances=instances)
            target_dir = Path(self.output_dir) / 'input.prometheus'
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            with open(Path(self.output_dir) / 'input.prometheus' / 'prometheus.toml', 'w', encoding='utf-8') as f:
                f.write(render_data)

    def vsphere(self):
        if self.instances.get('vsphere'):
            template = self._get_template('input.vsphere/vsphere.toml.j2')
            instances = self.instances['vsphere']['instance']
            render_data = template.render(instances=instances)
            target_dir = Path(self.output_dir) / 'input.vsphere'
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            with open(Path(self.output_dir) / 'input.vsphere' / 'vsphere.toml', 'w', encoding='utf-8') as f:
                f.write(render_data)

    def http_response(self):
        template = self._get_template('input.http_response/http_response.toml.j2')
        if self.instances.get('http_response'):
            instances = self.instances['http_response']['instance']
            render_data = template.render(instances=instances)
            target_dir = Path(self.output_dir) / 'input.http_response'
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            with open(Path(self.output_dir) / 'input.http_response' / 'http_response.toml', 'w', encoding='utf-8') as f:
                f.write(render_data)

    def net_response(self):
        template = self._get_template('input.net_response/net_response.toml.j2')
        if self.instances.get('net_response'):
            instances = self.instances['net_response']['instance']
            render_data = template.render(instances=instances)
            target_dir = Path(self.output_dir) / 'input.net_response'
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            with open(Path(self.output_dir) / 'input.net_response' / 'net_response.toml', 'w', encoding='utf-8') as f:
                f.write(render_data)

    def dns_query(self):
        template = self._get_template('input.dns_query/dns_query.toml.j2')
        if self.instances.get('dns_query'):
            instances = self.instances['dns_query']['instance']
            render_data = template.render(instances=instances)
            target_dir = Path(self.output_dir) / 'input.dns_query'
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            with open(Path(self.output_dir) / 'input.dns_query' / 'dns_query.toml', 'w', encoding='utf-8') as f:
                f.write(render_data)

    def snmp(self):
        if self.instances.get('snmp'):
            device_types = self.instances['snmp']['instances']
            for device_type in device_types:
                instances = self.instances['snmp']['instances'][device_type]
                jinja2_dir = Path(jinja2_path) / 'input.snmp'
                device_templates = glob(str(jinja2_dir / f'{device_type}_*.toml.j2'))
                if not device_templates:
                    continue
                for tmpl_path in device_templates:
                    tmpl_name = os.path.basename(tmpl_path)
                    base_name = tmpl_name.replace('.toml.j2', '')
                    template = self._get_template(f'input.snmp/{tmpl_name}')
                    render_data = template.render(instances=instances, config=self.instances['snmp']['config'])

                    target_dir = Path(self.output_dir) / 'input.snmp'
                    if not target_dir.exists():
                        target_dir.mkdir(parents=True, exist_ok=True)
                    
                    output_file = target_dir / f'{base_name}.toml'
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(render_data)

    def run(self):
        self.common('cpu')
        self.common('mem')
        self.common('net')
        self.common('disk')
        self.common('diskio')
        self.vsphere()
        self.ping()
        self.prometheus()   
        self.http_response()
        self.net_response()
        self.dns_query()
        self.snmp()