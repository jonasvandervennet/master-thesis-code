const composer = require('openwhisk-composer')

const name = 'tree_reduce';
const sep = '__';

function batch_per_2({value}) {
    let batched_arr = [];
    for (let i=0; i<value.length - 1; i+=2) {
        // TODO: checking each round is not that optimal, but does it matter for thesis?
        // each number value can be guarded as an object {value: number}
        if (typeof value[i] === "object"){
            batched_arr.push([value[i].value, value[i+1].value])
        } else {
            batched_arr.push([value[i], value[i+1]])
        }
    }
    return {value: batched_arr}  // guarded in object key value for use in map operation later
}

const batch_action = composer.action(`${name}${sep}batch`, { action: batch_per_2});

const reduction_branch = composer.action(`${name}${sep}reduction_branch`, { action: ({value}) => { return {value: value[0] + value[1]} } });

const reduction_sequence = composer.sequence(
    batch_action, 
    composer.map(reduction_branch),
);

module.exports = composer.sequence(
    composer.while(params => params.value.length > 1, reduction_sequence),
    composer.action(`${name}${sep}finalize`, { action: ({value}) => {return { value: value[0].value}}}))

/*
input_array: [1,2,3,4,5,6,7,8]
{
    "value": 36
}

input_array: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
{
    "value": 136
}
*/