import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenApplicationsSsh } from './token-applications-ssh';
import { MachineService } from '../../../../services/machine/machine.service';
import { of } from 'rxjs';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableDataSource } from '@angular/material/table';
import { MachineTokenData } from '../../../../model/machine/machine-token-data';
import { signal } from '@angular/core';
import { TokenSelectedContent } from '../../token.component';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';

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
    machineService.getToken.and.returnValue(of(mockResponse));

    component
      .fetchDataHandler({
        pageIndex: 0,
        pageSize: 10,
        sortby_sortdir: { active: 'id', direction: 'asc' },
        filterValue: '',
      })
      .subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });
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
    const result = component.processDataSource(mockResponse);
    expect(result[0]).toBe(mockResponse.result.value.length);
    expect(result[1] instanceof MatTableDataSource).toBeTrue();
  });

  it('should return object strings correctly', () => {
    const options = { key1: 'value1', key2: 'value2' };
    const result = component.getObjectStrings(options);
    expect(result).toEqual(['key1: value1', 'key2: value2']);
  });
});
