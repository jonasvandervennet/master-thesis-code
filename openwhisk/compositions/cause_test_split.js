const composer = require('openwhisk-composer')

const name = 'cause_test_split';
const sep = '__';

module.exports = composer.sequence(
    composer.action(`${name}${sep}origin`, { action: () => { return {"state": 1} } }),
    composer.action(`${name}${sep}branch`, { action: (state) => { state["state"] += 1; return state } }),
    composer.parallel(
        composer.sequence(
            composer.action(`${name}${sep}left1`, { action: (state) => { state["left"] = state["state"] - 1; return state } }),
            composer.action(`${name}${sep}left2`, { action: (state) => { state["left"] *= 2; return state } })
        ),
        composer.sequence(
            composer.action(`${name}${sep}right1`, { action: (state) => { state["right"] = state["state"] + 1; return state } }),
            composer.action(`${name}${sep}right2`, { action: (state) => { state["right"] *= 2; return state } })
        ),
    ),
    composer.action(`${name}${sep}combine`, { action: (state) => { return Object.assign(state["value"][0], state["value"][1]); } }),
    composer.action(`${name}${sep}stop`, { action: (state) => { return state } }),
);

/*
{
    "left": 2,
    "right": 6,
    "state": 2
}
*/