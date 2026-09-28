//SPDX-License-Identifier: Unlicensed

pragma solidity ^0.8.30;

import {IMisstep} from "./IMisstep.sol";

contract Challenge {
    IMisstep public MisstepAddr;

    constructor(address misstepAddress) {
        // It takes the huff address, it will apply the IMisstep rules
        MisstepAddr = IMisstep(misstepAddress);
    }

    // Forwards this to the Huff contract
    function isSolved() public view returns (bool) {
        return MisstepAddr.isSolved();
    }
}
