@both
Feature: Customer list

  Background:
    Given I am logged in as "owner@shop.com"

  Scenario: Seeded customers appear in the list
    Then I see "Carter" in the customer list
    And I see "Gonzalez" in the customer list
    And I see "Chen" in the customer list
    And I see "Johnson" in the customer list

  Scenario: Tap customer navigates to vehicle list
    When I tap "James Carter"
    Then I see a vehicle list screen with "James Carter" as the title
