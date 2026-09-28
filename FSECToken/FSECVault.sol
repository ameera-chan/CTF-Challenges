// SPDX-License-Identifier: Unlicensed

pragma solidity ^0.8.30;

import {FSECToken} from "./FSECToken.sol";

contract FSECVault {
    // stores contract address of FSECToken
    FSECToken public immutable i_token;
    // stores address of deployer
    address private immutable i_setup;

    // address1 -> balance1
    // address2 -> balance2
    // each address is mapped to its balance
    mapping(address => uint256) public s_balances;
    // each address is mapped to received status
    mapping(address => bool) public s_received;

    constructor(address _token) {
        i_token = FSECToken(_token);
        i_setup = msg.sender;
    }

    // related to the FSECToken contract that calls receiveToken
    function receiveToken(address _from, uint256 _amount) external {
        // if the caller is not the FSECToken contract, then revert
        if (msg.sender != address(i_token)) {
            revert();
        }
        // if deployer is not the sender in FSECToken contract, then return, else add the amount to the balance of the sender
        if (_from == i_setup) {
            return;
        }

        s_balances[_from] += _amount;
    }

    // if the caller has received the token, received == 1, then revert
    // else, set received to true and transfer 1 ether to the caller
    function tap() external {
        if (s_received[msg.sender]) {
            revert();
        }

        s_received[msg.sender] = true;
        i_token.transfer(msg.sender, 1 ether);
    }

    // if the caller has no balance, then revert
    // else, transfer the balance to the caller and set the balance to 0
    function withdraw() external {
        uint256 balance = s_balances[msg.sender];
        if (balance == 0) {
            revert();
        }

        // CEI - Check Effects Interactions pattern
        // Set the balance to 0 before transferring the token
        // ?v Reentrancy Attack
        i_token.transfer(msg.sender, balance);
        // withdrawal -20 times,
        s_balances[msg.sender] = 0;
    }

    function getBalance(address _user) external view returns (uint256) {
        return s_balances[_user];
    }

    // Solved condition, if the balance of the vault is 0, return true, else return false
    function isSolved() external view returns (bool) {
        return i_token.balanceOf(address(this)) == 0;
    }
}
