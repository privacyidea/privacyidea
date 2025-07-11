import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenApplicationsOfflineComponent } from './token-applications-offline.component';
import { signal } from '@angular/core';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { TokenSelectedContentKey } from '../../token.component';
import { MachineService } from '../../../../services/machine/machine.service';
import { MatTableDataSource } from '@angular/material/table';

describe('TokenApplicationsOffline', () => {
  let component: TokenApplicationsOfflineComponent;
  let fixture: ComponentFixture<TokenApplicationsOfflineComponent>;
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

    fixture = TestBed.createComponent(TokenApplicationsOfflineComponent);
    component = fixture.componentInstance;
    component.length = signal(0);
    component.pageSize = signal(10);
    component.pageIndex = signal(0);
    component.filterValue = signal('');
    component.sort = signal({
      active: 'serial',
      direction: 'asc',
    });
    component.dataSource = signal(
      new MatTableDataSource(
        Array.from({ length: component.pageSize() }, () => {
          const emptyRow: any = {};
          TokenApplicationsOfflineComponent.columnsKeyMap.forEach((column) => {
            emptyRow[column.key] = '';
          });
          return emptyRow;
        }),
      ),
    );
    component.fetchApplicationOfflineData = () => {};
    component.advancedApiFilter = [];

    machineService = TestBed.inject(
      MachineService,
    ) as jasmine.SpyObj<MachineService>;

    component.tokenSerial = signal<string>('');
    component.selectedContent =
      signal<TokenSelectedContentKey>('token_details');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
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
  });
});
