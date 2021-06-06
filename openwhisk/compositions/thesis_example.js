const composer = require('openwhisk-composer')

const l1 = composer.action(
    'l1', { action: () => { return {"left_state": 1} } }
);
const l2 = composer.action(
    'l2', { action:  (state) => { state["left_state"] += 7; return state } }
);
const left_branch = composer.sequence(l1, l2);

const right_branch = composer.action(
    'right_branch', { action: function () { return {"right_state": 2} } }
);

module.exports = composer.if(
    composer.action(
        'decision', { action: ({pw}) => { return { value: pw === 'abc123' } } }
    ),
    composer.parallel(left_branch, right_branch),
    composer.action(
        'failure', { action: function () { return { message: 'failure' } } })
    )