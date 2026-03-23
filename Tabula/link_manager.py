import os
import sys

class LinkManager:
    def create_junction(self, target, link_name):
        """Creates a Windows junction link"""
        try:
            os.symlink(target, link_name, target_is_directory=True)
            print(f'Junction created: {link_name} -> {target}')
        except OSError as e:
            print(f'Error creating junction: {e}')

    def create_symlink(self, target, link_name):
        """Creates a Windows symlink"""
        try:
            os.symlink(target, link_name)
            print(f'Symlink created: {link_name} -> {target}')
        except OSError as e:
            print(f'Error creating symlink: {e}')

    def validate_link(self, link_name):
        """Validates if a link exists"""
        exists = os.path.exists(link_name)
        return exists

    def track_link(self, link_name):
        """Tracks the target of a symlink or junction"""
        if self.validate_link(link_name):
            target = os.readlink(link_name)
            print(f'Link {link_name} points to: {target}')
        else:
            print(f'Link {link_name} does not exist.')
