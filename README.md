# Actions plugin for FIR - Fast Incident Response

[FIR](https://github.com/certsocietegenerale/FIR) (Fast Incident Response by [CERT Société générale](https://cert.societegenerale.com/)) is an cybersecurity incident management platform designed with agility and speed in mind. It allows for easy creation, tracking, and reporting of cybersecurity incidents.


# Features

This plugins allows you to assign actions to FIR business lines and manage countermeasures called 'Blocks'.

# Installation

!! `fir_actions` needs FIR pull requests certsocietegenerale/FIR#127 and certsocietegenerale/FIR#131 .

## Overview

Follow the generic plugin installation instructions in [the FIR wiki](https://github.com/certsocietegenerale/FIR/wiki/Plugins).

## Details

You should install it in the FIR _virtualenv_. 

```bash
(your_env)$ git clone https://github.com/gcrahay/fir_actions_plugin.git
(your_env)$ cd fir_actions_plugin
(your_env)$ python setup.py install

```

In *$FIR_HOME/fir/config/installed_app.txt*, add:

```
django_fsm
selectable
fir_actions
```

In your *$FIR_HOME*, launch:

```bash
(your_env)$ ./manage.py migrate
(your_env)$ ./manage.py collectstatic -y
```


# Usage

In the incident details view, you can add actions and blocks.

# Configuration

--

## User permissions

* `fir_actions.can_approve_block`: User can approve a countermeasure.
* `fir_actions.can_enforce_block`: User can enforce a countermeasure.

