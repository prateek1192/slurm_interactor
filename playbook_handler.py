import os
from tempfile import NamedTemporaryFile
from ansible.inventory import Inventory
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor import playbook_executor
from ansible.utils.display import Display

class Options(object):

    """
    Options to replace Ansible OptParser
    """
    def __init__(self, verbosity=None, inventory=None, listhosts=None,
        subset=None, module_paths=None, extra_vars=None, forks=None,
        ask_vault_pass=None, output_file=None, tags=None,
        skip_tags=None, one_line=None, tree=None, ask_sudo_pass=None,
        ask_su_pass=None, sudo=None, sudo_user=None, become=None,
        become_method=None, become_user=None, become_ask_pass=None,
        ask_pass=None, private_key_file=None, remote_user=None,
        connection=None, timeout=None, ssh_common_args=None,
        sftp_extra_args=None, scp_extra_args=None, ssh_extra_args=None,
        poll_interval=None, seconds=None, check=None, systax=None,
        diff=None, force_handlers = None, flush_cache=None, listtasks=None,
        listtags=None, module_path = None, vault_password_files=None,
        new_vault_password_file=None, syntax=None):
        
        self.verbosity = verbosity
        self.inventory = inventory
        self.listhosts = listhosts
        self.subset = subset
        self.module_paths = module_paths
        self.extra_vars = extra_vars
        self.forks = forks
        self.ask_vault_pass = ask_vault_pass
        self.output_file = output_file
        self.tags = tags
        self.skip_tags = skip_tags
        self.one_line = one_line
        self.tree = tree
        self.ask_sudo_pass = ask_sudo_pass
        self.ask_su_pass = ask_su_pass
        self.sudo = sudo
        self.sudo_user = sudo_user
        self.become = become
        self.become_method = become_method
        self.become_user = become_user
        self.become_ask_pass = become_ask_pass
        self.ask_pass = ask_pass
        self.private_key_file = private_key_file
        self.remote_user = remote_user
        self.connection = connection
        self.timeout = timeout
        self.ssh_common_args = ssh_common_args
        self.sftp_extra_args = sftp_extra_args
        self.scp_extra_args = scp_extra_args
        self.ssh_extra_args = ssh_extra_args
        self.poll_interval = poll_interval
        self.seconds = seconds
        self.check = check
        self.diff = diff
        self.force_handlers = force_handlers
        self.flush_cache = flush_cache
        self.listtasks = listtasks
        self.listtags = listtags
        self.module_path = module_path
	self.vault_password_files = vault_password_files,
        self.new_vault_password_file=None
        self.syntax=None

class Runner(object):

    def __init__(self, hostnames, playbook, private_key_file, run_data, become_pass,
                 verbosity=0):

        self.run_data = run_data

        self.options=Options()
        self.options.private_key_file = private_key_file
        self.options.verbosity = verbosity
        self.options.connection = 'ssh'
        self.options.become = True
        self.options.become_method = 'sudo'
        self.options.become_user = 'root'

        self.display = Display()
        self.display.verbosity = self.options.verbosity
        playbook_executor.verbosity = self.options.verbosity
        
        # Become pass Need if not logging in as user root
        passwords = {'become_pass' : become_pass}

        # Gets data from YAML/JSON files
        self.loader = DataLoader()
        # self.loader.set_vault_password(os.environ['VAULT_PASS'])

        # All the variables from all the various places
        self.variable_manager = VariableManager()
        self.variable_manager.extra_vars = self.run_data

        # Parse hosts
        # TODO Figure out a better way to parse hosts
        self.hosts = NamedTemporaryFile(delete=False)
	self.hosts.write("""[run_hosts]
        %s
        """ % hostnames)
        
        self.hosts.close()
        self.inventory = Inventory(loader = self.loader, variable_manager=self.variable_manager,
                                   host_list=self.hosts.name)
        self.variable_manager.set_inventory(self.inventory)

        # Playbook to run. Assumes it is local to this Python file
        pb_dir = os.path.dirname(__file__)
        playbook = "%s/%s" %(pb_dir, playbook)
        
         # Setup playbook executor, but don't run until run() called
        self.pbex = playbook_executor.PlaybookExecutor(
            playbooks=[playbook], 
            inventory=self.inventory, 
            variable_manager=self.variable_manager,
            loader=self.loader, 
            options=self.options, 
            passwords=passwords)


    def run(self):
        # Results of PlaybookExecutor
        self.pbex.run()
        stats = self.pbex._tqm._stats

        # Test if success for record_logs
        run_success = True
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            if t['unreachable'] > 0 or t['failures'] > 0:
                run_success = False

        # Dirty hack to send callback to save logs with data we want
        # Note that function "record_logs" is one I created and put into
        # the playbook callback file
        self.pbex._tqm.send_callback(
            'record_logs', 
            user_id=self.run_data['user_id'], 
            success=run_success
        )

        # Remove created temporary files
        os.remove(self.hosts.name)

        return stats
