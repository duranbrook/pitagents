@both
Feature: Authentication

  Scenario: Successful login
    Given the app is on the Login screen
    When I enter email "owner@shop.com" and password "testpass"
    And I tap "Sign In"
    Then I see the Customers list

  Scenario: Wrong password shows error
    Given the app is on the Login screen
    When I enter email "owner@shop.com" and password "wrongpass"
    And I tap "Sign In"
    Then I see a red error message beneath the Sign In button
    And I remain on the Login screen

  Scenario: Empty fields disable Sign In button
    Given the app is on the Login screen
    When the email field is empty
    Then the "Sign In" button is disabled or grayed out

  Scenario: Keyboard Return key submits login
    Given the app is on the Login screen
    And I have typed "owner@shop.com" in the email field
    And I have typed "testpass" in the password field
    When I press Return/Done on the keyboard
    Then the login request is submitted
    And I see the Customers list
