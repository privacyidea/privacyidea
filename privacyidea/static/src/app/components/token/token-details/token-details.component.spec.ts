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

class MockTokenService {
  getTokenDetails() {
    return of({
      result: {
        value: {
          tokens: [{
            active: true,
            revoked: false,
            container_serial: 'mock_serial'
          }]
        }
      }
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
    return of({result: {value: {containers: [{serial: 'container1'}, {serial: 'container2'}]}}});
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
      imports: [
        TokenDetailsComponent
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {provide: TokenService, useClass: MockTokenService},
        {provide: ContainerService, useClass: MockContainerService},
        {provide: ValidateService, useClass: MockValidateService}
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;
    component.serial = signal('Mock serial');
    component.tokenIsSelected = signal(false);
    component.active = signal(false);
    component.revoked = signal(false);

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
    });
  });

  it('should reset fail count', () => {
    spyOn(tokenService, 'resetFailCount').and.callThrough();
    component.resetFailCount();
    expect(tokenService.resetFailCount).toHaveBeenCalledWith('Mock serial');
  });

  it('should save token detail', () => {
    spyOn(tokenService, 'setTokenDetail').and.callThrough();
    component.saveDetail('key', 'value');
    expect(tokenService.setTokenDetail).toHaveBeenCalledWith('Mock serial', 'key', 'value');
  });

  it('should delete info', () => {
    spyOn(tokenService, 'deleteInfo').and.callThrough();
    component.deleteInfo('infoKey');
    expect(tokenService.deleteInfo).toHaveBeenCalledWith('Mock serial', 'infoKey');
  });

  it('should handle error when deleting info fails', () => {
    spyOn(tokenService, 'deleteInfo').and.returnValue(throwError(() => new Error('Deletion failed')));
    spyOn(console, 'error');
    component.deleteInfo('infoKey');
    expect(console.error).toHaveBeenCalledWith('Failed to delete info', jasmine.any(Error));
  });

  it('should test token', () => {
    spyOn(validateService, 'testToken').and.callThrough();
    component.otpOrPinToTest = 'testValue';
    component.testToken();
    expect(validateService.testToken).toHaveBeenCalledWith('Mock serial', 'testValue');
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

  it('should get container data', () => {
    spyOn(containerService, 'getContainerData').and.callThrough();
    component.showTokenDetail('Mock serial').subscribe(() => {
      expect(containerService.getContainerData).toHaveBeenCalledWith(1, 10);
    });
  });

  it('should resync OTP token', () => {
    component.fristOTPValue = 'otp1';
    component.secondOTPValue = 'otp2';

    spyOn(tokenService, 'resyncOTPToken').and.callThrough();
    component.resyncOTPToken();
    expect(tokenService.resyncOTPToken).toHaveBeenCalledWith('Mock serial', 'otp1', 'otp2');
  });

  it('should set token infos', () => {
    component.newInfo.set({key: 'infoKey', value: 'infoValue'});

    spyOn(tokenService, 'setTokenInfos').and.callThrough();
    component.saveInfo({});
    expect(tokenService.setTokenInfos).toHaveBeenCalledWith('Mock serial', jasmine.any(Object));
  });
});
