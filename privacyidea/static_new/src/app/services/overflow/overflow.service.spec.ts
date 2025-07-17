import { TestBed } from '@angular/core/testing';
import { OverflowService } from './overflow.service';

describe('OverflowService (DOM logic)', () => {
  let service: OverflowService;
  let querySelectorSpy: jest.SpyInstance;
  let getComputedSpy: jest.SpyInstance;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({});
    service = TestBed.inject(OverflowService);
  });

  afterEach(() => {
    querySelectorSpy?.mockRestore();
    getComputedSpy?.mockRestore();
  });

  it('isWidthOverflowing → true when clientWidth below threshold', () => {
    const selector = { clientWidth: 100 } as HTMLElement;
    querySelectorSpy = jest
      .spyOn(document, 'querySelector')
      .mockReturnValue(selector as any);

    expect(service.isWidthOverflowing('#selector', 150)).toBe(true);
    expect(service.isWidthOverflowing('#selector', 80)).toBe(false);
  });

  it('isWidthOverflowing returns false if element not found', () => {
    querySelectorSpy = jest
      .spyOn(document, 'querySelector')
      .mockReturnValue(null);
    expect(service.isWidthOverflowing('#missing', 100)).toBe(false);
  });

  it('isHeightOverflowing with numeric threshold', () => {
    const el = { clientHeight: 120 } as HTMLElement;
    querySelectorSpy = jest
      .spyOn(document, 'querySelector')
      .mockReturnValue(el as any);

    expect(
      service.isHeightOverflowing({ selector: '#selector', threshold: 200 }),
    ).toBe(true);
    expect(
      service.isHeightOverflowing({ selector: '#selector', threshold: 100 }),
    ).toBe(false);
  });

  it('isHeightOverflowing with thresholdSelector (padding trimmed)', () => {
    const element = { clientHeight: 100 } as HTMLElement;
    const thresholdEl = { clientHeight: 200 } as HTMLElement;

    querySelectorSpy = jest
      .spyOn(document, 'querySelector')
      .mockImplementation((sel: string) =>
        sel === '#target' ? element : thresholdEl,
      );

    getComputedSpy = jest
      .spyOn(window, 'getComputedStyle')
      .mockReturnValue({ paddingBottom: '20px' } as any);

    expect(
      service.isHeightOverflowing({
        selector: '#target',
        thresholdSelector: '#thr',
      }),
    ).toBe(true);

    (element as any).clientHeight = 350;
    expect(
      service.isHeightOverflowing({
        selector: '#target',
        thresholdSelector: '#thr',
      }),
    ).toBe(false);
  });

  it('isHeightOverflowing returns false if target element missing', () => {
    querySelectorSpy = jest
      .spyOn(document, 'querySelector')
      .mockReturnValue(null);
    expect(service.isHeightOverflowing({ selector: '#x' })).toBe(false);
  });

  it('getOverflowThreshold returns configured values', () => {
    expect(service.getOverflowThreshold('token_applications')).toBe(1500);
    expect(service.getOverflowThreshold('token_details')).toBe(1880);
    expect(service.getOverflowThreshold('container_details')).toBe(1880);
    expect(service.getOverflowThreshold('token_overview')).toBe(1880);
    expect(service.getOverflowThreshold('container_overview')).toBe(1880);
    expect(service.getOverflowThreshold('token_enrollment')).toBe(1240);
    expect(service.getOverflowThreshold('container_create')).toBe(1240);
    expect(service.getOverflowThreshold('token_get_serial')).toBe(1240);
    expect(service.getOverflowThreshold('unknown_page')).toBe(1920);
  });
});
