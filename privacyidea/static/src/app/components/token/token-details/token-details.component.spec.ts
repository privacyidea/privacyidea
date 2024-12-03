import {ComponentFixture, TestBed} from '@angular/core/testing';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {TokenDetailsComponent} from './token-details.component';
import {provideHttpClient} from '@angular/common/http';
import {signal} from '@angular/core';
import {TokenService} from '../../../services/token/token.service';
import {ContainerService} from '../../../services/container/container.service';
import {ValidateService} from '../../../services/validate/validate.service';
import {of, throwError} from 'rxjs';
import {FormControl} from '@angular/forms';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

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
    return of({result: {value: ['realm1', 'realm2']}});
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

  setTokenInfos() {
    return of(null);
  }

  deleteInfo() {
    return of(null);
  }
}

class MockContainerService {
  getContainerData() {
    return of({
      result: {
        value: {containers: [{serial: 'container1'}, {serial: 'container2'}]},
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
        {provide: TokenService, useClass: MockTokenService},
        {provide: ContainerService, useClass: MockContainerService},
        {provide: ValidateService, useClass: MockValidateService},
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;
    component.serial = signal('Mock serial');
    component.tokenIsSelected = signal(false);
    component.active = signal(false);
    component.revoked = signal(false);
    component.userOptions = signal(['user1', 'user2', 'admin']);
    component.containerOptions = signal(['container1', 'container2', 'admin-container']);
    component.tokengroupOptions.set(['group1', 'group2']);
    component.infoData.set([{
      keyMap: {key: 'info', label: 'Info'},
      value: {key1: 'value1', key2: 'value2'},
      isEditing: false
    }]);
    component.realmOptions.set(['realm1', 'realm2']);
    component.detailData.set([{
      keyMap: {key: 'container_serial', label: 'Container'},
      value: 'container1',
      isEditing: false
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
    component.showTokenDetail('Mock serial').subscribe(() => {
      expect(tokenService.getTokenDetails).toHaveBeenCalledWith('Mock serial');
      expect(component.detailData().length).toBeGreaterThan(0);
      expect(component.realmOptions().length).toBeGreaterThan(0);
      expect(component.active()).toBeTrue();
    });
  });

  it('should handle errors when loading token details fails', () => {
    spyOn(tokenService, 'getTokenDetails').and.returnValue(
      throwError(() => new Error('Error fetching token details'))
    );
    spyOn(console, 'error');
    component.showTokenDetail('Mock serial').subscribe({
      error: () => {
        expect(console.error).toHaveBeenCalledWith('Failed to get token details', jasmine.any(Error));
      },
    });
  });

  it('should handle empty data gracefully', () => {
    spyOn(tokenService, 'getTokenDetails').and.returnValue(of({result: {value: {tokens: []}}}));
    component.showTokenDetail('empty-serial').subscribe({
      next: () => {
        expect(component.detailData().length).toBe(0);
      },
    });
  });

  it('should display token details correctly', () => {
    const detailHeader = fixture.nativeElement.querySelector('.token-detail-header h2:last-child');
    expect(detailHeader.textContent).toContain('Mock serial');

    const containerCell = fixture.nativeElement.querySelector('.detail-table .detail-row');
    expect(containerCell.textContent).toContain('Container');
  });

  it('should filter user options correctly', () => {
    const result = component['_filterUserOptions']('user');
    expect(result).toEqual(['user1', 'user2']);
  });

  it('should save token detail', () => {
    spyOn(tokenService, 'setTokenDetail').and.callThrough();
    component.saveDetail('key', 'value');
    expect(tokenService.setTokenDetail).toHaveBeenCalledWith('Mock serial', 'key', 'value');
  });

  it('should handle error when deleting info fails', () => {
    spyOn(tokenService, 'deleteInfo').and.returnValue(throwError(() => new Error('Deletion failed')));
    spyOn(console, 'error');
    component.deleteInfo('infoKey');
    expect(console.error).toHaveBeenCalledWith('Failed to delete info', jasmine.any(Error));
  });

  it('should delete info', () => {
    spyOn(tokenService, 'deleteInfo').and.callThrough();
    component.deleteInfo('infoKey');
    expect(tokenService.deleteInfo).toHaveBeenCalledWith('Mock serial', 'infoKey');
  });

  it('should reset fail count', () => {
    spyOn(tokenService, 'resetFailCount').and.callThrough();
    component.resetFailCount();
    expect(tokenService.resetFailCount).toHaveBeenCalledWith('Mock serial');
  });

  it('should get container data', () => {
    spyOn(containerService, 'getContainerData').and.callThrough();
    component.showTokenDetail('Mock serial').subscribe(() => {
      expect(containerService.getContainerData).toHaveBeenCalledWith(1, 10);
    });
  });

  it('should assign container', () => {
    component.selectedContainer = new FormControl('container1');
    spyOn(containerService, 'assignContainer').and.callThrough();
    component.saveContainer();
    expect(containerService.assignContainer).toHaveBeenCalledWith('Mock serial', 'container1');
  });

  it('should unassign container', () => {
    component.selectedContainer = new FormControl('container1');
    spyOn(containerService, 'unassignContainer').and.callThrough();
    component.deleteContainer();
    expect(containerService.unassignContainer).toHaveBeenCalledWith('Mock serial', 'container1');
  });

  it('should set token infos', () => {
    component.newInfo.set({key: 'infoKey', value: 'infoValue'});

    spyOn(tokenService, 'setTokenInfos').and.callThrough();
    component.saveInfo({});
    expect(tokenService.setTokenInfos).toHaveBeenCalledWith('Mock serial', jasmine.any(Object));
  });

  it('should dynamically render info data', () => {
    const infoKeys = fixture.nativeElement.querySelectorAll('.info-container mat-list-item .object-item:first-child');
    expect(infoKeys.length).toBe(2);
    expect(infoKeys[0].textContent).toContain('key1');
    expect(infoKeys[1].textContent).toContain('key2');
  });

  it('should test and verify token', () => {
    spyOn(validateService, 'testToken').and.callThrough();
    component.otpOrPinToTest = '1234';
    component.testToken();
    component.verifyOTPValue()
    expect(validateService.testToken).toHaveBeenCalledWith('Mock serial', '1234');
  });

  it('should resync OTP token', () => {
    component.fristOTPValue = 'otp1';
    component.secondOTPValue = 'otp2';

    spyOn(tokenService, 'resyncOTPToken').and.callThrough();
    component.resyncOTPToken();
    expect(tokenService.resyncOTPToken).toHaveBeenCalledWith('Mock serial', 'otp1', 'otp2');
  });

  it('should resync OTP token on button click', () => {
    component.fristOTPValue = 'otp1';
    component.secondOTPValue = 'otp2';

    const resyncSpy = spyOn(tokenService, 'resyncOTPToken').and.callThrough();

    const resyncButton = fixture.nativeElement.querySelector('.pin-input-button button');
    resyncButton.click();
    expect(resyncSpy).toHaveBeenCalledWith('Mock serial', 'otp1', 'otp2');
  });

  it('should filter container options correctly', () => {
    const result = component['_filterContainerOptions']('admin');
    expect(result).toEqual(['admin-container']);
  });

  it('should handle edit and save for information details', () => {
    component.isEditingInfo = true;
    fixture.detectChanges();

    component.newInfo.set({key: 'newKey', value: 'newValue'});
    fixture.detectChanges();

    const saveButton = fixture.nativeElement.querySelector('.edit-button-container button:nth-child(1)');
    saveButton.click();
    fixture.detectChanges();

    const newInfo = component.infoData().find(info => info.keyMap.key === 'info')?.value;
    expect(newInfo).toEqual(jasmine.objectContaining({newKey: 'newValue'}));
  });
});
