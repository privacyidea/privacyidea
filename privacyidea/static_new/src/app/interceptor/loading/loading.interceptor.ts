import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize, share } from 'rxjs/operators';
import { LoadingService } from '../../services/loading/loading-service';
import { v4 as uuid } from 'uuid';

export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loadingService = inject(LoadingService);

  const loadingId = uuid();

  const sharedRequest$ = next(req).pipe(
    share(),
    finalize(() => {
      loadingService.removeLoading(loadingId);
    }),
  );
  console.log(req.url); //TODO
  loadingService.addLoading({ key: loadingId, observable: sharedRequest$ });

  return sharedRequest$;
};
