import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { TokenApplicationsComponent } from './token-applications.component';
import { TokenApplicationsSshComponent } from './token-applications-ssh/token-applications-ssh.component';
import { TokenApplicationsOfflineComponent } from './token-applications-offline/token-applications-offline.component';
import { MatSelectModule } from '@angular/material/select';
import { MachineService } from '../../../services/machine/machine.service';
import { ContentService } from '../../../services/content/content.service';
import { provideHttpClient } from '@angular/common/http';
import { makeMachineServiceMock } from '../../../../testing/mock-services';

describe('TokenApplicationsComponent (Jest)', () => {
  let fixture: ComponentFixture<TokenApplicationsComponent>;
  let component: TokenApplicationsComponent;
  const machineServiceMock = makeMachineServiceMock(); // ⬅️  new

  beforeEach(async () => {
    const mockContentService = {
      selectedContent: signal('token_applications'),
    };
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [
        TokenApplicationsComponent,
        TokenApplicationsSshComponent,
        TokenApplicationsOfflineComponent,
        MatSelectModule,
      ],
      providers: [
        provideHttpClient(),
        { provide: MachineService, useValue: machineServiceMock },
        { provide: ContentService, useValue: mockContentService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should default to "ssh" for selectedApplicationType', () => {
    expect(component.selectedApplicationType()).toBe('ssh');
  });

  it('should react when the machineService signal changes', () => {
    machineServiceMock.selectedApplicationType.set('offline');
    expect(component.selectedApplicationType()).toBe('offline');
  });
});
