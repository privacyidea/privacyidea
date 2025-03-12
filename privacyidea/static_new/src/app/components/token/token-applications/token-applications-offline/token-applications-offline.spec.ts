import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenApplicationsOffline } from './token-applications-offline';
import { signal } from '@angular/core';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { TokenSelectedContent } from '../../token.component';
import { MachineService } from '../../../../services/machine/machine.service';

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
