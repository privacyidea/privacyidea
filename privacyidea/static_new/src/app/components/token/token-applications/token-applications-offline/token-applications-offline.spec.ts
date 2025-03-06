import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenApplicationsOffline } from './token-applications-offline';
import { MachineService } from '../../../../services/machine/machine.service';
import { of } from 'rxjs';
import { MatTableDataSource } from '@angular/material/table';
import { MachineTokenData } from '../../../../model/machine/machine-token-data';
import { signal } from '@angular/core';
import { TokenSelectedContent } from '../../token.component';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('TokenApplicationsOffline', () => {
  let component: TokenApplicationsOffline;
  let fixture: ComponentFixture<TokenApplicationsOffline>;
  let machineService: jasmine.SpyObj<MachineService>;

  beforeEach(async () => {
    const machineServiceSpy = jasmine.createSpyObj('MachineService', [
      'getToken',
    ]);

    await TestBed.configureTestingModule({
      imports: [BrowserAnimationsModule],
      providers: [
        { provide: MachineService, useValue: machineServiceSpy },
        provideHttpClient(withInterceptorsFromDi()),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsOffline);
    component = fixture.componentInstance;
    machineService = TestBed.inject(
      MachineService,
    ) as jasmine.SpyObj<MachineService>;

    component.tokenSerial = signal<string>('');
    component.selectedContent = signal<TokenSelectedContent>('token_details');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should set token serial and selected content on selectToken', () => {
    component.selectToken('testSerial');
    expect(component.tokenSerial()).toBe('testSerial');
    expect(component.selectedContent()).toBe('token_details');
  });

  it('should split filters correctly', () => {
    const filterValue = 'serial: 123 hostname: testHost';
    const expected = { serial: '123', hostname: 'testHost' };
    expect(component.splitFilters(filterValue)).toEqual(expected);
  });

  it('should fetch data using machine service', () => {
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
    expect(result.data.length).toBe(1);
    const expectedDataSource = new MatTableDataSource(
      MachineTokenData.parseList(mockResponse.result.value),
    );
    expect(result.data).toEqual(expectedDataSource.data);
  });
});
