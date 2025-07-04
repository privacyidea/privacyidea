import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenApplicationsSshComponent } from './token-applications-ssh.component';
import { MatTabsModule } from '@angular/material/tabs';
import { signal } from '@angular/core';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { TokenSelectedContentKey } from '../../token.component';
import { MachineService } from '../../../../services/machine/machine.service';

describe('TokenApplicationsSsh', () => {
  let component: TokenApplicationsSshComponent;
  let fixture: ComponentFixture<TokenApplicationsSshComponent>;
  let machineService: jasmine.SpyObj<MachineService>;

  beforeEach(async () => {
    const machineServiceSpy = jasmine.createSpyObj('MachineService', [
      'getToken',
    ]);

    await TestBed.configureTestingModule({
      imports: [MatTabsModule, TokenApplicationsSshComponent],
      providers: [
        { provide: MachineService, useValue: machineServiceSpy },
        provideHttpClient(withInterceptorsFromDi()),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsSshComponent);
    component = fixture.componentInstance;
    machineService = TestBed.inject(
      MachineService,
    ) as jasmine.SpyObj<MachineService>;

    component.tokenSerial = signal<string>('');
    component.selectedContent =
      signal<TokenSelectedContentKey>('token_details');
    component.advancedApiFilter = [];
  });

  it('should create', () => {
    expect(component).toBeTruthy();
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
