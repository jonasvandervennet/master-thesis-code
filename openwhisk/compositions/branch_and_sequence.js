const composer = require('openwhisk-composer')

const name = 'branch_and_sequence';
const sep = '__';

const l1 = composer.action(`${name}${sep}l1`, { action: () => { return {"left_state": 1} } });
const l2 = composer.action(`${name}${sep}l2`, { action:  (state) => { state["left_state"] += 7;state["l2"] = 5; return state } });
const left_branch = composer.sequence(l1, l2);

const right_branch = composer.action(`${name}${sep}right_branch`, { action: function () { return {"right_state": 1} } });

module.exports = composer.if(
    composer.action(`${name}${sep}decision`, { action: ({password}) => { return { value: password === 'abc123' } } }),
    composer.parallel(left_branch, right_branch),
    composer.action(`${name}${sep}failure`, { action: function () { return { message: 'failure' } } }))

/*
{
    "value": [
        {
            "l2": 5,
            "left_state": 8
        },
        {
            "right_state": 1
        }
    ]
}
*/