from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextBrowser


PRIVACY_TEXT = """
<h2>Privacy & Data Usage</h2>
<p>This application stores data locally in an SQLite database in your user data directory.</p>
<ul>
 <li><b>Activity Titles & Instances:</b> Stored only locally. Window titles processed for categorization never leave your machine unless Gemini integration is enabled.</li>
 <li><b>Gemini API:</b> Only the prompt text (activity planning or classification requests) is sent if you provide an API key. Window titles are only sent if you explicitly map or categorize them using the AI features.</li>
 <li><b>API Key:</b> Stored in the system keyring when available; otherwise lightly obfuscated on disk.</li>
 <li><b>Telemetry:</b> Anonymous usage metrics (feature counts, non-identifying) are <i>disabled by default</i>. You can opt in via Settings.</li>
 <li><b>Logging:</b> Local rotating structured JSON logs. Potentially sensitive titles are redacted when feasible.</li>
</ul>
<p>You can purge data by deleting the SQLite file from the data directory.</p>
"""


class PrivacyPage(QWidget):  # pragma: no cover simple UI
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("Privacy Notice")
        browser = QTextBrowser()
        browser.setHtml(PRIVACY_TEXT)
        layout.addWidget(label)
        layout.addWidget(browser, 1)


__all__ = ["PrivacyPage"]
