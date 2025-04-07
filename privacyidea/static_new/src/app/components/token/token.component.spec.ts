import { ComponentFixture, fakeAsync, TestBed } from '@angular/core/testing';
import { Component } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { TokenComponent } from './token.component';
import { OverflowService } from '../../services/overflow/overflow.service';
import { NotificationService } from '../../services/notification/notification.service';
import { TokenDetailsComponent } from './token-details/token-details.component';
import { ContainerDetailsComponent } from './container-details/container-details.component';

@Component({
  selector: 'app-token-details',
  template: '',
  standalone: true,
})
class MockTokenDetailsComponent {
  showTokenDetail() {
    return of(null);
  }
}

@Component({
  selector: 'app-container-details',
  template: '',
  standalone: true,
})
class MockContainerDetailsComponent {
  showContainerDetail() {
    return of(null);
  }
}

class MockOverflowService {
  private _overflow = false;

  getOverflowThreshold() {
    return 1920;
  }

  setWidthOverflow(value: boolean) {
    this._overflow = value;
  }

  isWidthOverflowing(selector: string, threshold: number) {
    return this._overflow;
  }

  isHeightOverflowing(selector: string, threshold: number) {
    return this._overflow;
  }
}

class MockNotificationService {
  openSnackBar(msg: string) {
    console.warn('NotificationService.openSnackBar:', msg);
  }
}

class MockTokenService {
  tokenTypeOptions = [
    { value: 'type1', label: 'Type 1' },
    { value: 'type2', label: 'Type 2' },
  ];
}

describe('TokenComponent', () => {
  let component: TokenComponent;
  let fixture: ComponentFixture<TokenComponent>;
  let mockNotificationService: MockNotificationService;
  let mockOverflowService: MockOverflowService;
  let mockTokenService: MockTokenService;

  beforeEach(async () => {
    mockNotificationService = new MockNotificationService();
    mockOverflowService = new MockOverflowService();
    mockTokenService = new MockTokenService();

    await TestBed.configureTestingModule({
      imports: [BrowserAnimationsModule, TokenComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenComponent, useValue: TokenComponent },
        { provide: TokenDetailsComponent, useClass: MockTokenDetailsComponent },
        { provide: OverflowService, useValue: mockOverflowService },
        { provide: NotificationService, useValue: mockNotificationService },
        { provide: MockTokenService, useValue: mockTokenService },
      ],
    })
      .overrideComponent(TokenComponent, {
        remove: {
          imports: [TokenDetailsComponent, ContainerDetailsComponent],
        },
        add: {
          imports: [MockTokenDetailsComponent, MockContainerDetailsComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(TokenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have static tokenTypes defined', () => {
    expect(mockTokenService.tokenTypeOptions).toBeDefined();
    expect(mockTokenService.tokenTypeOptions.length).toBeGreaterThan(0);
  });

  it('should have default signal values', () => {
    expect(component.selectedContent()).toBe('token_overview');
    expect(component.tokenSerial()).toBe('');
    expect(component.containerSerial()).toBe('');
    expect(component.tokenIsActive()).toBeTrue();
    expect(component.revoked()).toBeTrue();
  });

  it('should refresh token details successfully', fakeAsync(() => {
    const onRefreshTokenDetails = spyOn(
      component,
      'onRefreshTokenDetails',
    ).and.returnValue(void 0);

    component.refreshTokenDetails.set(true);

    TestBed.flushEffects();
    fixture.detectChanges();

    expect(onRefreshTokenDetails).toHaveBeenCalled();
  }));

  it('should refresh container details successfully', fakeAsync(() => {
    const onRefreshContainerDetails = spyOn(
      component,
      'onRefreshContainerDetails',
    ).and.returnValue(void 0);

    component.refreshContainerDetails.set(true);

    TestBed.flushEffects();
    fixture.detectChanges();

    expect(onRefreshContainerDetails).toHaveBeenCalled();
  }));

  it('should show token card outside the drawer if overflowService returns false', () => {
    mockOverflowService.setWidthOverflow(false);
    fixture.detectChanges();

    const cardOutsideDrawer = fixture.nativeElement.querySelector(
      'app-token-card.margin-right-1',
    );
    const drawer = fixture.nativeElement.querySelector('mat-drawer');

    expect(cardOutsideDrawer).toBeTruthy();
    expect(drawer).toBeNull();
  });

  it('should show token card in drawer if overflowService returns true', () => {
    mockOverflowService.setWidthOverflow(true);
    fixture.detectChanges();

    const cardOutsideDrawer = fixture.nativeElement.querySelector(
      'app-token-card.margin-right-1',
    );
    const drawer = fixture.nativeElement.querySelector('mat-drawer');

    expect(cardOutsideDrawer).toBeNull();
    expect(drawer).toBeTruthy();
  });
});
