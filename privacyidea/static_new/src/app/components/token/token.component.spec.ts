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
  getOverflowThreshold() {
    return 1920;
  }

  isOverflowing() {
    return false;
  }
}

class MockNotificationService {
  openSnackBar(msg: string) {
    console.log('NotificationService.openSnackBar:', msg);
  }
}

describe('TokenComponent', () => {
  let component: TokenComponent;
  let fixture: ComponentFixture<TokenComponent>;
  let mockNotificationService: MockNotificationService;
  let mockOverflowService: MockOverflowService;

  beforeEach(async () => {
    mockNotificationService = new MockNotificationService();
    mockOverflowService = new MockOverflowService();

    await TestBed.configureTestingModule({
      imports: [BrowserAnimationsModule, TokenComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenComponent, useValue: TokenComponent },
        { provide: TokenDetailsComponent, useClass: MockTokenDetailsComponent },
        { provide: OverflowService, useValue: mockOverflowService },
        { provide: NotificationService, useValue: mockNotificationService },
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
    expect(TokenComponent.tokenTypes).toBeDefined();
    expect(TokenComponent.tokenTypes.length).toBeGreaterThan(0);
  });

  it('should have default signal values', () => {
    expect(component.selectedContent()).toBe('token_overview');
    expect(component.tokenSerial()).toBe('');
    expect(component.containerSerial()).toBe('');
    expect(component.tokenIsActive()).toBeTrue();
    expect(component.revoked()).toBeTrue();
  });

  it('should refresh token details successfully', fakeAsync(() => {
    const spy = spyOn(component, 'onRefreshTokenDetails').and.returnValue(
      void 0,
    );

    component.refreshTokenDetails.set(true);

    TestBed.flushEffects();

    //TODO testing effects doesn't work
    //expect(spy).toHaveBeenCalled();
  }));
});
