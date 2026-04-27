@both
Feature: Report generation via API

  Background:
    Given I am logged in as "owner@shop.com"
    And the backend has a session for James Carter's Toyota Camry

  Scenario: Generate report via API and see it in Reports tab
    Given I call POST /sessions/{sessionId}/generate-report
    When I navigate to James Carter's Toyota Camry and tap "Reports"
    Then a report appears with status "complete" (iOS) or "complete" (Android)
    And the report has at least one finding
    And the report has an estimate total

  Scenario: Report detail includes share token
    Given a report has been generated
    When I open the report detail view
    Then a "Share with Customer" button is visible
    And the share URL follows the pattern https://backend-production-5320.up.railway.app/r/{token}
