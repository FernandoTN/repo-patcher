const { getUniqueValues, processData } = require('../src/utils');

describe('Utils', () => {
    test('getUniqueValues should return unique values from array', () => {
        const input = [1, 2, 2, 3, 3, 4];
        const expected = [1, 2, 3, 4];
        const result = getUniqueValues(input);
        expect(result).toEqual(expected);
    });

    test('processData should extract values from objects', () => {
        const input = [
            { value: 'a', other: 1 },
            { value: 'b', other: 2 }
        ];
        const expected = ['a', 'b'];
        const result = processData(input);
        expect(result).toEqual(expected);
    });
});