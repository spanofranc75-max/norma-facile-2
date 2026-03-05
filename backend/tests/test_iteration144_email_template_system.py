"""
Iteration 144: Email Template System Tests
Tests the dynamic email template generation and email sending functionality:
1. Frontend generateEmailTemplate function creates correct templates based on conformity %
2. Email preview panel has proper data-testid attributes and functionality
3. Backend POST /api/sopralluoghi/{id}/invia-email accepts custom subject/body
"""

import pytest
import requests
import os
import re
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ==========================================
# FRONTEND CODE VERIFICATION TESTS
# ==========================================

class TestEmailTemplateCodeStructure:
    """Verify email template generation code structure in frontend"""
    
    def test_generate_email_template_function_exists(self):
        """Verify generateEmailTemplate function exists in SopralluogoWizardPage.js"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "const generateEmailTemplate = ()" in content, "generateEmailTemplate function should exist"
        print("PASS: generateEmailTemplate function exists")
    
    def test_urgent_threshold_conformity_below_40(self):
        """Verify urgent template triggers when conformity < 40%"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Check isUrgent logic
        assert "const isUrgent = conf < 40" in content, "isUrgent threshold should be conf < 40"
        print("PASS: Urgent threshold set at conformity < 40%")
    
    def test_warning_threshold_conformity_40_to_65(self):
        """Verify warning template triggers when conformity 40-65%"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Check isWarning logic
        assert "const isWarning = conf >= 40 && conf < 65" in content, "isWarning threshold should be 40-65"
        print("PASS: Warning threshold set at conformity 40-65%")
    
    def test_urgent_subject_has_urgente_prefix(self):
        """Verify URGENTE prefix in subject for urgent cases"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "'URGENTE - '" in content, "Subject should include 'URGENTE - ' prefix for urgent cases"
        print("PASS: URGENTE prefix present for urgent cases")
    
    def test_warning_subject_has_attenzione_prefix(self):
        """Verify ATTENZIONE prefix in subject for warning cases"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "'ATTENZIONE - '" in content, "Subject should include 'ATTENZIONE - ' prefix for warning cases"
        print("PASS: ATTENZIONE prefix present for warning cases")
    
    def test_urgent_body_has_art_2051_reference(self):
        """Verify Art. 2051 C.C. reference in urgent email body"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "Art. 2051 C.C." in content, "Urgent body should reference Art. 2051 C.C."
        assert '"Colpa Grave"' in content, "Urgent body should mention 'Colpa Grave'"
        print("PASS: Art. 2051 C.C. and Colpa Grave references present")
    
    def test_email_body_includes_variant_prices(self):
        """Verify email body includes variant prices from varianti A/B/C"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Check priceLines generation
        assert "const varianti = analisi.varianti || {}" in content, "Should access analisi.varianti"
        assert "const priceLines = ['A', 'B', 'C'].map(k =>" in content, "Should map over A, B, C variants"
        assert "v.costo_stimato" in content, "Should access costo_stimato for prices"
        print("PASS: Variant prices (A/B/C costo_stimato) included in email body")
    
    def test_email_body_includes_variant_page_reference(self):
        """Verify email body includes page reference for variants"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Check variantPage logic
        assert "const variantPage = analisi.rischi?.length > 3 ? '7' : '6'" in content, "Should calculate variant page"
        assert "A pagina ${variantPage}" in content, "Body should reference the variant page"
        print("PASS: Variant page reference included in email body")
    
    def test_warning_body_also_has_art_2051_reference(self):
        """Verify Art. 2051 C.C. also mentioned in warning template"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Count Art. 2051 references - should appear in both urgent and warning
        count = content.count("Art. 2051 C.C.")
        assert count >= 2, f"Art. 2051 C.C. should appear at least twice (urgent + warning), found {count}"
        print("PASS: Art. 2051 C.C. appears in both urgent and warning templates")


class TestEmailPreviewPanelStructure:
    """Verify email preview panel UI elements have proper data-testid attributes"""
    
    def test_email_subject_input_has_testid(self):
        """Verify email subject input has data-testid='email-subject-input'"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert 'data-testid="email-subject-input"' in content, "Email subject input should have data-testid"
        print("PASS: data-testid='email-subject-input' present")
    
    def test_email_body_input_has_testid(self):
        """Verify email body textarea has data-testid='email-body-input'"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert 'data-testid="email-body-input"' in content, "Email body textarea should have data-testid"
        print("PASS: data-testid='email-body-input' present")
    
    def test_email_preview_download_pdf_button_has_testid(self):
        """Verify 'Scarica PDF (Anteprima)' button has data-testid='email-preview-download-pdf'"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert 'data-testid="email-preview-download-pdf"' in content, "Download PDF button should have data-testid"
        assert "Scarica PDF (Anteprima)" in content, "Button should have 'Scarica PDF (Anteprima)' text"
        print("PASS: data-testid='email-preview-download-pdf' and button text present")
    
    def test_confirm_send_email_button_has_testid(self):
        """Verify send button has data-testid='btn-confirm-send-email'"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert 'data-testid="btn-confirm-send-email"' in content, "Send email button should have data-testid"
        print("PASS: data-testid='btn-confirm-send-email' present")
    
    def test_send_button_disabled_when_subject_or_body_empty(self):
        """Verify send button is disabled when subject or body is empty"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Check for the disabled logic
        assert "disabled={sendingEmail || !emailSubject.trim() || !emailBody.trim()}" in content, \
            "Send button should be disabled when subject or body is empty"
        print("PASS: Send button disabled when subject/body empty")
    
    def test_email_confirm_dialog_has_testid(self):
        """Verify email preview panel/dialog has data-testid='email-confirm-dialog'"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert 'data-testid="email-confirm-dialog"' in content, "Email preview dialog should have data-testid"
        print("PASS: data-testid='email-confirm-dialog' present")
    
    def test_email_state_variables_exist(self):
        """Verify email state variables exist in component"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "const [emailSubject, setEmailSubject] = useState('')" in content, "emailSubject state should exist"
        assert "const [emailBody, setEmailBody] = useState('')" in content, "emailBody state should exist"
        assert "const [showEmailConfirm, setShowEmailConfirm] = useState(false)" in content, "showEmailConfirm state should exist"
        print("PASS: Email state variables (emailSubject, emailBody, showEmailConfirm) present")


class TestHandleSendEmailFunction:
    """Verify handleSendEmail function sends subject/body in POST body"""
    
    def test_handle_send_email_posts_subject_and_body(self):
        """Verify handleSendEmail sends subject and body in POST body"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Check handleSendEmail posts subject and body
        assert "body: { subject: emailSubject, body: emailBody }" in content, \
            "handleSendEmail should POST {subject: emailSubject, body: emailBody}"
        print("PASS: handleSendEmail sends subject and body in POST body")
    
    def test_handle_send_email_calls_invia_email_endpoint(self):
        """Verify handleSendEmail calls the /invia-email endpoint"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "/invia-email" in content, "Should call /invia-email endpoint"
        assert "method: 'POST'" in content, "Should use POST method"
        print("PASS: handleSendEmail calls POST /invia-email endpoint")


# ==========================================
# BACKEND ENDPOINT TESTS
# ==========================================

class TestBackendInviaEmailEndpoint:
    """Verify backend /invia-email endpoint accepts custom subject/body"""
    
    def test_backend_endpoint_signature_accepts_payload(self):
        """Verify backend endpoint accepts payload dict parameter"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        # Check function signature
        assert "payload: dict = None" in content, "Endpoint should accept 'payload: dict = None'"
        print("PASS: Backend endpoint accepts 'payload: dict = None'")
    
    def test_backend_extracts_subject_from_payload(self):
        """Verify backend extracts subject from payload"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        assert 'payload.get("subject"' in content, "Backend should extract subject from payload"
        print("PASS: Backend extracts 'subject' from payload")
    
    def test_backend_extracts_body_from_payload(self):
        """Verify backend extracts body from payload"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        assert 'payload.get("body"' in content, "Backend should extract body from payload"
        print("PASS: Backend extracts 'body' from payload")
    
    def test_backend_fallback_when_subject_empty(self):
        """Verify backend has fallback when subject is empty"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        # Check fallback logic - "if not subject:"
        assert "if not subject:" in content, "Backend should check if subject is empty"
        print("PASS: Backend has fallback for empty subject")
    
    def test_backend_fallback_when_body_empty(self):
        """Verify backend has fallback when body is empty"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        # Check fallback logic - "if not body:"
        assert "if not body:" in content, "Backend should check if body is empty"
        print("PASS: Backend has fallback for empty body")
    
    def test_backend_uses_custom_subject_in_email(self):
        """Verify backend passes custom subject to email service"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        # The send_email_with_attachment should receive subject variable
        assert "subject=subject" in content, "Backend should pass subject to email service"
        print("PASS: Backend passes custom subject to email service")
    
    def test_backend_uses_custom_body_in_email(self):
        """Verify backend passes custom body to email service"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        # The send_email_with_attachment should receive body variable
        assert "body=body" in content, "Backend should pass body to email service"
        print("PASS: Backend passes custom body to email service")
    
    def test_backend_saves_email_subject_to_db(self):
        """Verify backend saves email_subject to database after sending"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        assert '"email_subject": subject' in content, "Backend should save email_subject to DB"
        print("PASS: Backend saves email_subject to database")


# ==========================================
# EMAIL TEMPLATE CONTENT VERIFICATION
# ==========================================

class TestEmailTemplateContent:
    """Detailed verification of email template content"""
    
    def test_urgent_body_mentions_rischio_penale(self):
        """Verify urgent body mentions 'Rischio Penale'"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "Rischio Penale" in content, "Urgent body should mention 'Rischio Penale'"
        print("PASS: Urgent body mentions 'Rischio Penale'")
    
    def test_urgent_body_mentions_rischio_assicurativo(self):
        """Verify urgent body mentions 'Rischio Assicurativo'"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "Rischio Assicurativo" in content, "Urgent body should mention 'Rischio Assicurativo'"
        print("PASS: Urgent body mentions 'Rischio Assicurativo'")
    
    def test_email_includes_client_name(self):
        """Verify email body includes client name"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "Gentile ${clientName}" in content, "Email should start with 'Gentile ${clientName}'"
        print("PASS: Email includes client name in greeting")
    
    def test_email_includes_document_number(self):
        """Verify email body includes document number"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "${docNum}" in content, "Email should include document number"
        print("PASS: Email includes document number")
    
    def test_email_includes_indirizzo(self):
        """Verify email body includes indirizzo"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "${indirizzo}" in content, "Email should include indirizzo"
        print("PASS: Email includes indirizzo")
    
    def test_email_includes_conformity_percentage(self):
        """Verify email body includes conformity percentage"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "${conf}%" in content, "Email should include conformity percentage"
        print("PASS: Email includes conformity percentage")
    
    def test_normal_body_no_art_2051(self):
        """Verify normal template (>65%) does NOT mention Art. 2051 with grave implications"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # The normal template (else block) starts around line 352
        # Extract just the normal body template
        normal_start = content.find("} else {\n            body = `Gentile")
        assert normal_start > 0, "Should find normal template"
        
        normal_section = content[normal_start:normal_start + 800]
        
        # Normal template should NOT have "Colpa Grave" or "Rischio Penale"
        assert '"Colpa Grave"' not in normal_section, "Normal template should not mention Colpa Grave"
        assert "Rischio Penale" not in normal_section, "Normal template should not mention Rischio Penale"
        print("PASS: Normal template (>65% conformity) has no severe warnings")
    
    def test_subject_includes_cancello_and_indirizzo(self):
        """Verify subject includes 'Cancello' and the indirizzo"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "Esito Perizia Tecnica Cancello ${indirizzo}" in content, \
            "Subject should include 'Esito Perizia Tecnica Cancello ${indirizzo}'"
        print("PASS: Subject includes 'Esito Perizia Tecnica Cancello' and indirizzo")


# ==========================================
# INTEGRATION FLOW TEST
# ==========================================

class TestEmailIntegrationFlow:
    """Test the complete flow from button click to email sending"""
    
    def test_btn_send_email_triggers_generate_template(self):
        """Verify 'Invia via Email' button triggers generateEmailTemplate"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Check that btn-send-email onClick calls generateEmailTemplate
        assert 'data-testid="btn-send-email"' in content, "btn-send-email should exist"
        assert "onClick={generateEmailTemplate}" in content, "btn-send-email should call generateEmailTemplate"
        print("PASS: btn-send-email triggers generateEmailTemplate")
    
    def test_generate_template_sets_show_email_confirm_true(self):
        """Verify generateEmailTemplate sets showEmailConfirm to true"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # At end of generateEmailTemplate function
        assert "setShowEmailConfirm(true)" in content, "generateEmailTemplate should setShowEmailConfirm(true)"
        print("PASS: generateEmailTemplate sets showEmailConfirm to true to show panel")
    
    def test_email_preview_panel_conditionally_rendered(self):
        """Verify email preview panel only shows when showEmailConfirm is true"""
        frontend_file = "/app/frontend/src/pages/SopralluogoWizardPage.js"
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        assert "{showEmailConfirm && (" in content, "Email panel should be conditionally rendered"
        print("PASS: Email preview panel conditionally rendered based on showEmailConfirm")


# ==========================================
# API ENDPOINT STRUCTURE TEST (without auth)
# ==========================================

class TestAPIEndpointExists:
    """Verify the API endpoint is properly configured"""
    
    def test_api_endpoint_route_registered(self):
        """Verify /invia-email route is registered in sopralluogo router"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        assert '@router.post("/{sopralluogo_id}/invia-email")' in content, \
            "POST /invia-email route should be registered"
        print("PASS: POST /{sopralluogo_id}/invia-email route registered")
    
    def test_api_endpoint_requires_authentication(self):
        """Verify endpoint requires authentication"""
        backend_file = "/app/backend/routes/sopralluogo.py"
        with open(backend_file, 'r') as f:
            content = f.read()
        
        # Find the invia_perizia_email function and check it has Depends(get_current_user)
        assert "user: dict = Depends(get_current_user)" in content, \
            "Endpoint should require authentication via get_current_user"
        print("PASS: Endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
