// https://github.com/apache/openwhisk/blob/master/docs/conductors.md#conductor-annotation

function main(params) {
    let step = params.$step || 0
    delete params.$step
    switch (step) {
        case 0: return { action: 'triple', params, state: { $step: 1 } }
        case 1: return { action: 'increment', params, state: { $step: 2 } }
        case 2: return { params }
    }
}