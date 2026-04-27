@both
Feature: Vehicle list

  Background:
    Given I am logged in as "owner@shop.com"
    And I have navigated to James Carter's vehicle list

  Scenario: Seeded vehicle appears
    Then I see "2019 Toyota Camry" in the vehicle list

  Scenario: Vehicle year displays without comma
    Then the row shows "2019" not "2,019"

  Scenario: Create a new vehicle
    When I tap the add (+) button
    And I fill in Year "2021", Make "Honda", Model "Civic"
    And I tap "Save"
    Then "2021 Honda Civic" appears in the vehicle list

  Scenario: Delete a vehicle
    Given "2021 Honda Civic" exists in the vehicle list
    When I swipe left on "2021 Honda Civic" and confirm delete
    Then "2021 Honda Civic" is no longer in the list
