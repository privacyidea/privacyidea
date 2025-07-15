import { TestBed } from '@angular/core/testing';
import { TableUtilsService } from './table-utils.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MatTableDataSource } from '@angular/material/table';

describe('TableUtilsService', () => {
  let service: TableUtilsService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        TableUtilsService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(TableUtilsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('emptyDataSource', () => {
    it('returns a MatTableDataSource with the requested number of blank rows', () => {
      const cols = [
        { key: 'id', label: 'ID' },
        { key: 'name', label: 'Name' },
      ];
      const ds = service.emptyDataSource<{ id: string; name: string }>(3, cols);

      expect(ds).toBeInstanceOf(MatTableDataSource);
      expect(ds.data.length).toBe(3);
      ds.data.forEach((row) => expect(row).toEqual({ id: '', name: '' }));
    });
  });

  describe('parseFilterString', () => {
    it('captures multi‑word values when no later label is found', () => {
      const r = service.parseFilterString(
        'username: Alice status: active some words',
        ['username', 'status'],
      );

      expect(r.filterPairs).toEqual([
        { key: 'username', value: 'alice' },
        { key: 'status', value: 'active some words' },
      ]);
      expect(r.remainingFilterText).toBe('');
    });

    it('handles composite labels like "infokey & infovalue"', () => {
      const r = service.parseFilterString(
        'infokey: model infovalue: 42 extra',
        ['infokey & infovalue'],
      );
      expect(r.filterPairs).toEqual([
        { key: 'infokey', value: 'model' },
        { key: 'infovalue', value: '42 extra' },
      ]);
      expect(r.remainingFilterText).toBe('');
    });
  });

  describe('toggleKeywordInFilter', () => {
    it('adds a missing keyword placeholder', () => {
      expect(service.toggleKeywordInFilter('', 'username')).toBe('username: ');
    });

    it('removes an existing keyword (idempotent)', () => {
      const once = service.toggleKeywordInFilter('username: ', 'username');
      expect(once).toBe('');

      const twice = service.toggleKeywordInFilter(
        'machineid: 1 resolver: x',
        'machineid & resolver',
      );
      expect(twice).toBe('');
    });
  });

  describe('toggleBooleanInFilter', () => {
    it('cycles through true → false → (removed)', () => {
      const step1 = service.toggleBooleanInFilter({
        keyword: 'active',
        currentValue: '',
      });
      expect(step1).toBe('active: true');

      const step2 = service.toggleBooleanInFilter({
        keyword: 'active',
        currentValue: step1,
      });
      expect(step2).toBe('active: false');

      const step3 = service.toggleBooleanInFilter({
        keyword: 'active',
        currentValue: step2,
      });
      expect(step3).toBe('');
    });
  });

  it('recordsFromText converts a filter string to a record map', () => {
    const rec = service.recordsFromText('k1: v1 k2: v2');
    expect(rec).toEqual({ k1: 'v1', k2: 'v2' });
  });

  it.each([
    ['username', true],
    ['realms', true],
    ['unknown', false],
  ])('isLink("%s") → %s', (key, expected) => {
    expect(service.isLink(key)).toBe(expected);
  });

  describe('getClassForColumn', () => {
    it('returns highlight-disabled when locked', () => {
      expect(service.getClassForColumn('any', { locked: true })).toBe(
        'highlight-disabled',
      );
    });

    it('returns the correct class for active column', () => {
      expect(service.getClassForColumn('active', { active: true })).toBe(
        'highlight-true-clickable',
      );
      expect(service.getClassForColumn('active', { active: false })).toBe(
        'highlight-false-clickable',
      );
    });

    it('returns the correct class for failcount column', () => {
      expect(
        service.getClassForColumn('failcount', { failcount: 0, maxfail: 5 }),
      ).toBe('highlight-true');
      expect(
        service.getClassForColumn('failcount', { failcount: 2, maxfail: 5 }),
      ).toBe('highlight-warning-clickable');
      expect(
        service.getClassForColumn('failcount', { failcount: 5, maxfail: 5 }),
      ).toBe('highlight-false-clickable');
    });
  });

  describe('getTooltipForColumn', () => {
    it('returns tooltip for active column', () => {
      expect(service.getTooltipForColumn('active', { active: true })).toBe(
        'Deactivate Token',
      );
      expect(service.getTooltipForColumn('active', { active: false })).toBe(
        'Activate Token',
      );
    });

    it('returns Locked / Revoked first', () => {
      expect(service.getTooltipForColumn('active', { locked: true })).toBe(
        'Locked',
      );
      expect(service.getTooltipForColumn('failcount', { revoked: true })).toBe(
        'Revoked',
      );
    });
  });

  describe('getDisplayText', () => {
    it.each([
      [{ active: true }, 'active'],
      [{ active: false }, 'deactivated'],
      [{ active: true, locked: true }, 'locked'],
      [{ active: false, revoked: true }, 'revoked'],
      [{ active: '' }, ''], // empty strings short‑circuit
    ])('maps element → "%s"', (element, expected) => {
      expect(service.getDisplayText('active', element)).toBe(expected);
    });
  });
});
