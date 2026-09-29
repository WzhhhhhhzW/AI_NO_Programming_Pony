"""No user config or network; assert both modes require API configuration."""
from test_concept_ui import ConceptUITests
from PyQt6.QtWidgets import QLineEdit
from unittest.mock import patch
from dialogs import APISettingsDialog


class ConfigUITests(ConceptUITests):
    def test_missing_config_blocks_both_modes_and_unlock(self):
        w=self.window
        w.user_api_key=w.user_api_base_url=w.user_endpoint_id=''
        w._init_client()
        for index in (0,1,0):
            w.difficulty_combo.setCurrentIndex(index)
            w._unlock_send()
            self.assertIsNone(w.client)
            self.assertFalse(w.btn_send.isEnabled())
            self.assertFalse(w.txt_input.isEnabled())
            with patch('ui_main.APIAdvisor',side_effect=AssertionError('No configuration')):
                self.assertFalse(w._ensure_advisor())
        w.user_api_key='synthetic-key'
        w.user_api_base_url='https://api.example.test/v1'
        w.user_endpoint_id='selected-model'
        w._init_client()
        self.assertTrue(w.btn_send.isEnabled())
        w.client.close()

    def test_settings_reject_missing_fields_and_mask_key(self):
        d=APISettingsDialog()
        self.assertEqual(d.edit_key.echoMode(),QLineEdit.EchoMode.Password)
        with patch('dialogs.QMessageBox.warning') as warn:
            d.accept()
            self.assertEqual(d.result(),0)
            warn.assert_called_once()
        d.edit_key.setText('synthetic-key')
        d.edit_url.setText('https://api.example.test/v1')
        d.edit_model.setText('chosen-model')
        d.accept()
        self.assertEqual(d.result(),1)
        d.deleteLater()

    def test_failure_still_exposes_partial_changes_for_undo(self):
        with patch.object(self.window,'_render_ai_changes') as render:
            self.window._on_advisor_failed('test failure after Edit')
            render.assert_called_once()
