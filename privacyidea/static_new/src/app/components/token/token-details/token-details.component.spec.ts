import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TokenDetailsComponent } from './token-details.component';
import { provideHttpClient } from '@angular/common/http';
import { signal } from '@angular/core';
import { TokenService } from '../../../services/token/token.service';
import { ContainerService } from '../../../services/container/container.service';
import { ValidateService } from '../../../services/validate/validate.service';
import { of, throwError } from 'rxjs';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

class MockTokenService {
  getTokenDetails() {
    return of({
      result: {
        value: {
          tokens: [
            {
              active: true,
              revoked: false,
              container_serial: 'mock_serial',
              realms: ['realm1', 'realm2'],
            },
          ],
        },
      },
    });
  }

  getRealms() {
    return of({ result: { value: ['realm1', 'realm2'] } });
  }

  resetFailCount() {
    return of(null);
  }

  setTokenDetail() {
    return of(null);
  }

  assignUser() {
    return of(null);
  }

  unassignUser() {
    return of(null);
  }

  setPin() {
    return of(null);
  }

  setRandomPin() {
    return of(null);
  }

  resyncOTPToken() {
    return of(null);
  }
}

class MockContainerService {
  getContainerData() {
    return of({
      result: {
        value: { containers: [{ serial: 'container1' }, { serial: 'container2' }] },
      },
    });
  }

  assignContainer() {
    return of(null);
  }

  unassignContainer() {
    return of(null);
  }
}

class MockValidateService {
  testToken() {
    return of(null);
  }
}

describe('TokenDetailsComponent', () => {
  let component: TokenDetailsComponent;
  let fixture: ComponentFixture<TokenDetailsComponent>;
  let tokenService: TokenService;
  let containerService: ContainerService;
  let validateService: ValidateService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ValidateService, useClass: MockValidateService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;
    component.tokenSerial = signal('Mock serial');
    component.active = signal(false);
    component.revoked = signal(false);
    component.containerOptions = signal(['container1', 'container2', 'admin-container']);
    component.tokengroupOptions = signal(['group1', 'group2']);
    component.infoData = signal([{
      keyMap: { key: 'info', label: 'Info' },
      value: { key1: 'value1', key2: 'value2' },
      isEditing: signal(false)
    }]);
    component.realmOptions = signal(['realm1', 'realm2']);
    component.tokenDetailData = signal([{
      keyMap: { key: 'container_serial', label: 'Container' },
      value: 'container1',
      isEditing: signal(false)
    }]);
    tokenService = TestBed.inject(TokenService);
    containerService = TestBed.inject(ContainerService);
    validateService = TestBed.inject(ValidateService);

    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load token details on initialization', () => {
    spyOn(tokenService, 'getTokenDetails').and.callThrough();
    component.showTokenDetail().subscribe(() => {
      expect(tokenService.getTokenDetails).toHaveBeenCalledWith('Mock serial');
      expect(component.tokenDetailData().length).toBeGreaterThan(0);
      expect(component.realmOptions().length).toBeGreaterThan(0);
      expect(component.active()).toBeTrue();
    });
  });

  it('should handle errors when loading token details fails', () => {
    spyOn(tokenService, 'getTokenDetails').and.returnValue(
      throwError(() => new Error('Error fetching token details.'))
    );
    spyOn(console, 'error');
    component.showTokenDetail().subscribe({
      error: () => {
        expect(console.error).toHaveBeenCalledWith('Failed to get token details.', jasmine.any(Error));
      },
    });
  });

  it('should handle empty data gracefully', () => {
    spyOn(tokenService, 'getTokenDetails').and.returnValue(of({ result: { value: { tokens: [] } } }));
    component.showTokenDetail().subscribe({
      next: () => {
        expect(component.tokenDetailData().length).toBe(0);
      },
    });
  });

  it('should display token details correctly', () => {
    const detailHeader = fixture.nativeElement.querySelector('.details-header h3:last-child');
    expect(detailHeader.textContent).toContain('Mock serial');
  });


  it('should save token detail', () => {
    spyOn(tokenService, 'setTokenDetail').and.callThrough();
    component.saveDetail('key', 'value');
    expect(tokenService.setTokenDetail).toHaveBeenCalledWith('Mock serial', 'key', 'value');
  });

  it('should reset fail count', () => {
    spyOn(tokenService, 'resetFailCount').and.callThrough();
    component.resetFailCount();
    expect(tokenService.resetFailCount).toHaveBeenCalledWith('Mock serial');
  });

  it('should get container data', () => {
    spyOn(containerService, 'getContainerData').and.callThrough();
    component.showTokenDetail().subscribe(() => {
      expect(containerService.getContainerData).toHaveBeenCalledWith(1, 10);
      expect(component.containerOptions().length).toBe(3);
    });
  });

  it('should assign container', () => {
    component.selectedContainer = signal('container1');
    spyOn(containerService, 'assignContainer').and.callThrough();
    component.saveContainer();
    expect(containerService.assignContainer).toHaveBeenCalledWith('Mock serial', 'container1');
  });

  it('should unassign container', () => {
    component.selectedContainer = signal('container1');
    spyOn(containerService, 'unassignContainer').and.callThrough();
    component.deleteContainer();
    expect(containerService.unassignContainer).toHaveBeenCalledWith('Mock serial', 'container1');
  });

  it('should filter container options correctly', () => {
    const result = component['_filterContainerOptions']('admin');
    expect(result).toEqual(['admin-container']);
  });
});

