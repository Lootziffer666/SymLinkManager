class RelocationLedger:
    def __init__(self):
        self.relocations = []

    def add_relocation(self, item, old_location, new_location, date):
        relocation = {
            'item': item,
            'old_location': old_location,
            'new_location': new_location,
            'date': date
        }
        self.relocations.append(relocation)

    def export_relocations(self):
        return self.relocations

    def get_relocation_history(self):
        return sorted(self.relocations, key=lambda x: x['date'])
