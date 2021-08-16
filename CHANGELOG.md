CHANGELOG
=========



iocage.py (2020-08-16)
----------------------

* Use f-strings everywhere.

* Fix create cmd strings. -r -n values were interchanged.	

* Keep BSD license.

* Facts updated in doc.

* Add (c) 2021 vbotka@gamil.com to the license.

* All contibutors added to the authors in doc.


iocage_test.yml (2020-08-11)
----------------------------

* All tests put into tagged block/rescue.
* Module assert used to test rescued results and some of the
  successful results as well.
* Optional debug output.
* All tests passed.
  Controller: Ubuntu 20.04, ansible-base 2.10.12-1ppa~focal
  Node: FreeBSD 13.0-RELEASE, py38-iocage-1.2_9


iocage.py (2020-08-11)
----------------------

* Copy iocage to iocage.py

* Changed license to GPLv3

  # GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

  ansible-test sanity ERROR: plugins/modules/system/iocage.py:0:0:
  missing-gplv3-license: GPLv3 license header not found in the first
  20 lines of the module

  https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_in_groups.html#creating-a-new-collection
  "All other files shipped with Ansible, including all modules, must
  be licensed under the GPL license (GPLv3 or later)."

* Add 'yes'/'no' to the list of valid Booleans
  example:
  if _val in ['yes', 'on', True]:

* Add function _command_fail

* Add conversion of types and text transformation for Module utilities
  https://docs.ansible.com/ansible/latest/reference_appendices/module_utils.html

* Removed quotation from the strings in examples. Quotation kept
  around IP.

* Changed Boolean properties to 'true'/'false'.

  EXAMPLES = '''
  ...
    properties:
      ip4_addr: 'lo1|10.1.0.5'
      boot: true
      allow_sysvipc: true

* Removed option "force". It was used in the function *jail_start*
  only, but the command "iocage start ..." does not recognize *force*.

* Removed options "stdout" and "stderr" from module_args

* Removed empty defaults (name="", properties={}, ). The default of
  such options will be None. This will simplify the conditions (if
  name is not None). If needed such variables must be declared in the
  code (properties={}).

* Default user for executing commands in a jail is root. Moved this
  assignment from the reading of module.params to module_args

* Return _changed instead of values True/False

* Add messages when state=absent

  _msg = "Jail {0} removed from iocage_templates.".format(name)
  _msg = "Jail {0} removed from iocage_jails.".format(name)
  _msg = "Jail {0} is already absent.".format(name)

* Add rc to the result of state=exec