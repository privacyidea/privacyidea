import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenApplicationsSsh } from './token-applications-ssh';
import { MatTabsModule } from '@angular/material/tabs';
import { signal } from '@angular/core';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { TokenSelectedContent } from '../../token.component';
import { MachineService } from '../../../../services/machine/machine.service';

describe('TokenApplicationsSsh', () => {
  let component: TokenApplicationsSsh;
  let fixture: ComponentFixture<TokenApplicationsSsh>;
  let machineService: jasmine.SpyObj<MachineService>;

  beforeEach(async () => {
    const machineServiceSpy = jasmine.createSpyObj('MachineService', [
      'getToken',
    ]);

    await TestBed.configureTestingModule({
      imports: [MatTabsModule, TokenApplicationsSsh],
      providers: [
        { provide: MachineService, useValue: machineServiceSpy },
        provideHttpClient(withInterceptorsFromDi()),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsSsh);
    component = fixture.componentInstance;
    machineService = TestBed.inject(
      MachineService,
    ) as jasmine.SpyObj<MachineService>;

    component.tokenSerial = signal<string>('');
    component.selectedContent = signal<TokenSelectedContent>('token_details');
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should set token serial and selected content on selectToken', () => {
    component.selectToken('test-serial');
    expect(component.tokenSerial()).toBe('test-serial');
    expect(component.selectedContent()).toBe('token_details');
  });

  it('should fetch data using fetchDataHandler', () => {
    const mockResponse = {
      result: {
        value: [
          {
            id: 1,
            machine_id: 'machine1',
            options: {},
            resolver: 'resolver1',
            serial: 'serial1',
            type: 'type1',
          },
        ],
      },
    };
  });

  it('should process data source correctly', () => {
    const mockResponse = {
      result: {
        value: [
          {
            id: 1,
            machine_id: 'machine1',
            options: {},
            resolver: 'resolver1',
            serial: 'serial1',
            type: 'type1',
          },
        ],
      },
    };
    /*
    const result = component.processDataSource(mockResponse);
    expect(result instanceof MatTableDataSource).toBeTrue();
    expect(result.data.length).toBe(1);
    expect(result.data[0].id).toBe(1);
    expect(result.data[0].machine_id).toBe('machine1');
    expect(result.data[0].options).toEqual({});
    expect(result.data[0].resolver).toBe('resolver1');
    expect(result.data[0].serial).toBe('serial1');
    expect(result.data[0].type).toBe('type1');
    */
  });

  it('should return object strings correctly', () => {
    const options = { key1: 'value1', key2: 'value2' };
    const result = component.getObjectStrings(options);
    expect(result).toEqual(['key1: value1', 'key2: value2']);
  });
});
