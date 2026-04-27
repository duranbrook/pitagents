Feature: Inspect and Recording

  Background:
    Given I am logged in as "owner@shop.com"

  @both
  Scenario: Inspect tab shows customer grid
    When I tap the "Inspect" tab
    Then I see a grid of customer cards including "James Carter"

  @both
  Scenario: Select customer then vehicle navigates to recording screen
    When I tap "James Carter" in the Inspect grid
    Then I see James Carter's vehicles
    When I tap "2019 Toyota Camry"
    Then I see the agent/recording screen for that vehicle

  @manual
  Scenario: Start recording captures audio (physical device only)
    Given I am on the agent/recording screen for a vehicle
    When I tap the record button
    Then the recording timer starts
    And the waveform or microphone indicator becomes active

  @manual
  Scenario: Stop recording triggers report generation (physical device only)
    Given a recording is in progress
    When I tap the stop button
    Then the app calls POST /sessions/{id}/generate-report
    And after processing completes, a new report appears in the Reports tab for that vehicle
