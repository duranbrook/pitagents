@both
Feature: Reports

  Background:
    Given I am logged in as "owner@shop.com"

  Scenario: Reports tab shows report list
    Given at least one report exists for James Carter's Toyota Camry
    When I navigate to James Carter's Toyota Camry and tap "Reports"
    Then I see at least one report row with a title and status badge

  Scenario: Tap report opens detail view
    Given at least one report exists for James Carter's Toyota Camry
    When I navigate to James Carter's Toyota Camry, tap "Reports", and tap a report row
    Then I see the vehicle card at the top
    And I see a list of inspection findings
    And I see an estimate table with a Grand Total

  Scenario: High severity finding shows red Urgent badge
    Given a report exists with a finding of severity "high"
    When I open the report detail view
    Then that finding row shows a red "Urgent" badge

  Scenario: No reports shows empty state
    Given James Carter's Toyota Camry has no reports
    When I navigate to that vehicle and tap "Reports"
    Then I see "No Reports" (iOS) or "No reports yet." (Android)

  Scenario: Share button is present on detail view
    Given at least one report exists for James Carter's Toyota Camry
    When I open any report detail view
    Then I see a "Share with Customer" button
