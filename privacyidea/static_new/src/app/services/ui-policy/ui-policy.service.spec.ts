import { TestBed } from '@angular/core/testing';
import { UiPolicyService } from './ui-policy.service';

describe('UiPolicyService', () => {
  // Renamed describe block to match the service name
  let service: UiPolicyService; // Changed 'component' to 'service' for clarity

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [UiPolicyService], // Provide the service here
    });

    // Get an instance of the service from the TestBed injector
    service = TestBed.inject(UiPolicyService);
  });

  it('should be created', () => {
    // Changed description to reflect service creation
    expect(service).toBeTruthy();
  });

  // Add more specific tests for your service's methods here
  // Example:
  // it('should return true for a valid policy', () => {
  //   expect(service.checkPolicy('somePolicy')).toBeTrue();
  // });
});
