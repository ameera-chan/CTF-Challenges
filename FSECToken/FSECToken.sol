//SPDX-License-Identifier: Unlicensed

pragma solidity ^0.8.30;

// ERC-20
import {ERC20} from "openzeppelin-contracts/contracts/token/ERC20/ERC20.sol";

contract FSECToken is ERC20 {
    // 20 ether , 20 FSECTokens
    uint256 public constant TOTAL_SUPPLY = 20 ether;

    // ERC-20 - smart contract that represents a token - FSECToken
    // receiver -> msg.sender , sender -> address(0)
    constructor() ERC20("FSECToken", "FSEC") {
        // create 20 FSECTokens and gives it to msg.sender
        _mint(msg.sender, TOTAL_SUPPLY);
    }

    // _mint automatically calls update function, transfer/mint/burn
    // if the sender is is address[0] then it is mint, if receiver is address[0] then it is burn
    function _update(
        address from,
        address to,
        uint256 amount
    ) internal override {
        // call the _update from ERC20 - do the transfer/burn/mint depending on the address
        super._update(from, to, amount);

        // If "to" and "from" is not address(0) it is transfer
        // If "to" is address(0) it is burn
        // If "from" is address(0) it is mint
        if (from != address(0) && to != address(0)) {
            // sending the from and amoount value to the receiver
            // the receiver is exepected to have a function called receiveToken(address,uint256)
            // if have, then the function will be run
            // if the receiver is not a smart contract, and is just a normal wallet, it will still succeed but no code will be run
            bytes memory data = abi.encodeWithSignature(
                "receiveToken(address,uint256)",
                from,
                amount
            );
            (bool success, ) = to.call(data);

            if (!success) revert(); // if the transfer fails, then revert the transaction
        }
    }
}
