# MCP Snapshot Management and Reporting using Ansible

This collection contains a module (and templates) dedicated to reporting on Snapshot usage within the NTT Ltd. MCP

**Author:** Ken Sinfield <ken.sinfield@cis.ntt.com>

## Requirements

### Reporting System Requirements

* <250 servers 500 of RAM 1 vCPUs
* 250-500 servers 1GB of RAM 1 vCPUs
* \>500 servers 2GB of RAM 2 vCPUs
* Running 2 simultaneous reports against 2 different MCPs: Double the RAM and vCPU count

### Ansible Version

* >2.9

### Python Modules

* requests
* configparser
* PyOpenSSL
* netaddr
* Jinja2
* PyYaml

To install these modules execute:

> pip install --user jmespath requests configparser PyOpenSSL netaddr Jinja2 PyYaml


## Ansible Collection(s)

Additionally, the NTTMCP-MCP Ansible collection is required.

https://galaxy.ansible.com/nttmcp/mcp

> ansible-galaxy collection install nttmcp.mcp -f


## Authentication

Configure Cloud Control credentials by creating/editing a `.nttmcp` file in your home directory containing the following information:

    [nttmcp]
    NTTMCP_API: api-<geo>.mcp-services.net
    NTTMCP_API_VERSION: 2.10
    NTTMCP_PASSWORD: mypassword
    NTTMCP_USER: myusername

OR

Use environment variables:

    set +o history
    export NTTMCP_API=api-<geo>.mcp-services.net
    export NTTMCP_API_VERSION=2.10
    export NTTMCP_PASSWORD=mypassword
    export NTTMCP_USER=myusername
    set -o history


## Usage

* **kensinfield.snapshot_report.report** -- Use to generate a report showing servers with snapshots enabled and any failed snapshots.

* **region** and **datacenter** are required arguments while **network_domain** is optional

* If **network_domain** is omitted then the module will report on all servers for the user's organization within the MCP

* The module must be run from the collections folder where the templates/ and reports/ directories are located or the templates/ and reports/ folder from the collection must be copied to the directory from which the module will be run

> ansible localhost -c local -m kensinfield.snapshot_report.report -a"region=<region> datacenter=<MCP ID> network_domain=<network domain name>"
> ansible localhost -c local -m kensinfield.snapshot_report.report -a"region=na datacenter=NA9"
