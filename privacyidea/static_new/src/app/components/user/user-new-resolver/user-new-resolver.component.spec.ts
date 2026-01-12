import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserNewResolverComponent } from './user-new-resolver.component';
import { ResolverService } from '../../../services/resolver/resolver.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MockResolverService } from '../../../../testing/mock-services/mock-resolver-service';
import { MockNotificationService, MockPiResponse } from "../../../../testing/mock-services";
import { ResourceStatus, signal } from '@angular/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('UserNewResolverComponent', () => {
  let component: UserNewResolverComponent;
  let fixture: ComponentFixture<UserNewResolverComponent>;
  let resolverService: MockResolverService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserNewResolverComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ResolverService, useClass: MockResolverService },
        { provide: NotificationService, useClass: MockNotificationService },
        {
          provide: Router,
          useValue: {
            navigate: jest.fn(),
            navigateByUrl: jest.fn()
          }
        }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UserNewResolverComponent);
    component = fixture.componentInstance;
    resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should pre-fill form when a resolver is selected (edit mode)', async () => {
    const resolverName = 'test-resolver';
    const resolverData = {
      [resolverName]: {
        resolvername: resolverName,
        type: 'passwdresolver',
        data: {
          fileName: '/tmp/test'
        }
      }
    };

    resolverService.selectedResolverName.set(resolverName);

    const resourceValue = {
      result: {
        status: true,
        value: resolverData
      }
    };
    (resolverService.selectedResolverResource as any).value = signal(resourceValue);

    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.isEditMode).toBeTruthy();
    expect(component.resolverName).toBe(resolverName);
    expect(component.resolverType).toBe('passwdresolver');
    expect(component.formData['fileName']).toBe('/tmp/test');

    const inputElement = fixture.nativeElement.querySelector('input[placeholder="/etc/passwd"]');
    expect(inputElement.value).toBe('/tmp/test');
  });

  it('should pre-fill form for sqlresolver when selected (edit mode)', async () => {
    const resolverName = 'sql-res';
    const resolverData = {
      [resolverName]: {
        resolvername: resolverName,
        type: 'sqlresolver',
        data: {
          Database: 'testdb',
          Driver: 'mysql'
        }
      }
    };

    resolverService.selectedResolverName.set(resolverName);
    const resourceValue = {
      result: {
        status: true,
        value: resolverData
      }
    };
    (resolverService.selectedResolverResource as any).value = signal(resourceValue);

    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.resolverType).toBe('sqlresolver');
    const dbInput = fixture.nativeElement.querySelector('input[placeholder="YourDatabase"]');
    expect(dbInput.value).toBe('testdb');
  });

  it('should re-fill form when resource reloads', async () => {
    const resolverName = 'test-resolver';
    const initialData = {
      [resolverName]: {
        resolvername: resolverName,
        type: 'passwdresolver',
        data: { fileName: '/initial' }
      }
    };

    resolverService.selectedResolverName.set(resolverName);
    const resourceValue = signal({
      result: { status: true, value: initialData }
    });
    const resourceStatus = signal(ResourceStatus.Resolved);
    (resolverService.selectedResolverResource as any).value = resourceValue;
    (resolverService.selectedResolverResource as any).status = resourceStatus;

    fixture.detectChanges();
    await fixture.whenStable();
    expect(component.formData['fileName']).toBe('/initial');

    resourceStatus.set(ResourceStatus.Reloading);
    fixture.detectChanges();

    const updatedData = {
      [resolverName]: {
        resolvername: resolverName,
        type: 'passwdresolver',
        data: { fileName: '/updated' }
      }
    };
    resourceValue.set({ result: { status: true, value: updatedData } });
    resourceStatus.set(ResourceStatus.Resolved);

    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.formData['fileName']).toBe('/updated');
  });

  it('should show error and not redirect when postResolver returns status true but value -1', async () => {
    const resolverName = 'test-error';
    component.resolverName = resolverName;
    component.resolverType = 'sqlresolver';

    const errorResponse = new MockPiResponse<number, { description: string }>({
      result: {
        status: true,
        value: -1
      },
      detail: {
        description: 'Unable to connect to database.'
      }
    });

    resolverService.postResolver.mockReturnValue(of(errorResponse));
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    const router = TestBed.inject(Router);

    component.onSave();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining('Unable to connect to database.')
    );
    expect(router.navigateByUrl).not.toHaveBeenCalled();
    expect(component.resolverName).toBe(resolverName);
  });

  it('should show error when postResolverTest returns status true but value -1', async () => {
    component.resolverType = 'sqlresolver';

    const errorResponse = new MockPiResponse<number, { description: string }>({
      result: {
        status: true,
        value: -1
      },
      detail: {
        description: 'Connection test failed.'
      }
    });

    resolverService.postResolverTest.mockReturnValue(of(errorResponse));
    const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    component.onTest();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(
      expect.stringContaining('Connection test failed.')
    );
  });
});
