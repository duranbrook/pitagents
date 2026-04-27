@both
Feature: Messages

  Background:
    Given I am logged in as "owner@shop.com"
    And I have navigated to James Carter's Toyota Camry
    And I am on the Messages tab

  Scenario: Send a message and see it immediately
    When I type "Your car is ready" in the message input
    And I tap the Send button
    Then an outbound bubble with text "Your car is ready" appears immediately
    And the message input is empty after send

  Scenario: Keyboard Send key sends message and dismisses keyboard
    When I tap the message input (keyboard appears)
    And I type "Test message"
    And I press the Send key on the keyboard
    Then an outbound bubble with "Test message" appears
    And the keyboard is dismissed

  Scenario: Send button dismisses keyboard
    When I tap the message input (keyboard appears)
    And I type "Another message"
    And I tap the Send icon button
    Then the keyboard is dismissed

  Scenario: Switch channel to Email
    When I select "Email" from the channel selector
    And I type "Invoice ready" and tap Send
    Then the bubble shows the "EMAIL" channel label
