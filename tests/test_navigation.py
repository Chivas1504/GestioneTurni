"""Navigation must preserve the visit; changing calling mode must propagate."""
import unittest
import test_reliability as support
from app.controller import AppController
from app.window import MainWindow
from main import prepare_account_config


class NavigationTests(unittest.TestCase):
    def setUp(self):
        store = support.AccountStore()
        account = store.create('Navigation test', 'test-password')
        prepare_account_config(account)
        self.controller = AppController(store)
        self.window = MainWindow(self.controller)
        self.addCleanup(self.window.close)

    def test_menu_pages_are_embedded_and_preserve_visit_timer(self):
        self.controller.set_queue_active(True)
        self.controller.set_number(7, action='increment')
        timer = self.controller.get_current_patient_timer()
        for name in ('dashboard', 'history', 'settings', 'home'):
            self.window.show_page(name)
            support.APP.processEvents()
            self.assertEqual(self.window.current_page, name)
            self.assertEqual(timer, self.controller.get_current_patient_timer())
            if name != 'home':
                self.assertFalse(self.window.pages[name].widget().isWindow())
                self.assertFalse(self.window.pages[name].widget().isModal())
        self.controller.open_history(self.controller.dashboard_window)
        self.assertEqual(self.window.current_page, 'history')
        self.controller.history_window.close_button.click()
        self.assertEqual(self.window.current_page, 'home')

    def test_home_mode_saves_and_cannot_be_reverted_by_settings_draft(self):
        self.window.show_page('settings')
        page = self.window.pages['settings'].widget()
        self.assertFalse(hasattr(page, 'queue_mode_combo'))
        self.window.show_page('home')
        self.window.mode_surname_button.click()
        self.assertEqual(self.controller.queue_mode, 'surname')
        self.assertEqual(self.controller.shared_state.get_local_doctor()['queue_mode'], 'surname')
        self.assertEqual(self.controller.account_store.get(self.controller.doctor_id)['queue_mode'], 'surname')
        self.window.show_page('settings')
        page.doctor_name_input.setText('Medico aggiornato')
        page.save_button.click()
        self.assertEqual(self.window.current_page, 'home')
        self.assertEqual(self.controller.queue_mode, 'surname')
        self.assertEqual(self.controller.doctor_name, 'Medico aggiornato')
        self.assertNotIn('settings', self.window.pages)
        self.window.mode_number_button.click()
        self.assertEqual(self.controller.queue_mode, 'number')

    def test_cancel_discards_unsaved_settings(self):
        self.window.show_page('settings')
        page = self.window.pages['settings'].widget()
        page.doctor_name_input.setText('Da scartare')
        page.cancel_button.click()
        self.window.show_page('settings')
        self.assertEqual(self.window.pages['settings'].widget().doctor_name_input.text(), self.controller.doctor_name)

    def test_history_distinguishes_empty_history_from_empty_search(self):
        self.window.show_page('history')
        page = self.window.pages['history'].widget()
        page.history = []
        page.apply_filter()
        self.assertIn('Nessuna visita registrata', page.empty_label.text())
        self.assertTrue(page.table.isHidden())
        page.history = [{'date': '2026-11-19'}]
        page.search_input.setText('nessuna-corrispondenza')
        self.assertIn('Nessun risultato', page.empty_label.text())
        self.assertFalse(page.export_button.isEnabled())
        page.search_input.clear()
        self.assertTrue(page.empty_label.isHidden())
        self.assertEqual(page.table.rowCount(), 1)
        self.assertTrue(page.export_button.isEnabled())

    def test_home_prefix_saves_syncs_and_survives_settings(self):
        combo = self.window.queue_prefix_combo
        combo.setCurrentIndex(combo.findData('B'))
        self.assertEqual(self.controller.queue_prefix, 'B')
        self.assertEqual(self.controller.shared_state.get_local_doctor()['queue_prefix'], 'B')
        self.assertEqual(self.controller.account_store.get(self.controller.doctor_id)['queue_prefix'], 'B')
        self.window.show_page('settings')
        page = self.window.pages['settings'].widget()
        self.assertFalse(hasattr(page, 'queue_prefix_input'))
        page.save_button.click()
        self.assertEqual(self.controller.queue_prefix, 'B')
        self.window.mode_surname_button.click()
        self.assertFalse(combo.isEnabled())
        self.window.mode_number_button.click()
        self.assertTrue(combo.isEnabled())
        self.assertEqual(combo.currentData(), 'B')
        combo.setCurrentIndex(0)
        self.assertEqual(self.controller.queue_prefix, '')

if __name__ == '__main__':
    unittest.main()
