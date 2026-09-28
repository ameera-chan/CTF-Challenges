//SPDX-License-Identifier: Unlicensed

pragma solidity ^0.8.30;

interface IMisstep {
    function enter(
        bytes32 hash,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external payable;
    function isSolved() external view returns (bool);
}
